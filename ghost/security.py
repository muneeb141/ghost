"""Shared authentication boundaries; no consumer business app dependencies."""

import hashlib
import re

import frappe
from frappe import _


def require_owned_ghost(ghost_email):
	settings = frappe.get_single("Ghost Settings")
	actor = frappe.session.user
	domain = (settings.ghost_email_domain or "guest.local").lower()
	pattern = rf"ghost_(?:[0-9a-f]{{8}}|[0-9a-f]{{32}})@{re.escape(domain)}"
	if not settings.enable_ghost_feature or not actor or actor == "Guest" or actor != ghost_email:
		frappe.throw(_("An authenticated Ghost session owned by you is required"), frappe.PermissionError)
	if not re.fullmatch(pattern, actor):
		frappe.throw(_("This account is not an anonymous Ghost identity"), frappe.PermissionError)
	user = frappe.db.get_value("User", actor, ["enabled", "user_type"], as_dict=True, for_update=True)
	role = settings.ghost_role or "Ghost"
	if (
		not user
		or not user.enabled
		or user.user_type != "Website User"
		or role not in frappe.get_roles(actor)
	):
		frappe.throw(_("This Ghost session cannot be converted"), frappe.PermissionError)
	return actor


def require_enabled_user(user):
	if user in (None, "", "Guest", "Administrator") or not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("This account cannot authenticate"), frappe.AuthenticationError)
	if frappe.db.get_value("User", user, "user_type") == "System User":
		settings = frappe.get_single("Ghost Settings")
		if not settings.get("allow_system_user_login"):
			frappe.throw(_("System user OTP login is disabled"), frappe.PermissionError)


def require_test_sandbox(settings):
	if getattr(settings, "sandbox_mode", 0) and not frappe.flags.in_test:
		frappe.throw(
			_("Fixed OTP sandbox mode is available only inside automated tests"), frappe.PermissionError
		)


def limit_verification(identity, purpose, limit=5):
	"""Count guesses outside the DB transaction so rejected requests cannot reset them."""
	cache = frappe.cache()
	ip = getattr(frappe.local, "request_ip", None) or "internal"
	for scope, value, maximum in (("identity", identity, limit), ("ip", ip, 30)):
		digest = hashlib.sha256(f"{scope}:{value}:{purpose}".encode()).hexdigest()
		key = cache.make_key(f"ghost:verify:{digest}")
		count = cache.eval(
			"local n = redis.call('INCR', KEYS[1]); "
			"if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return n",
			1,
			key,
			300,
		)
		if count > maximum:
			frappe.throw(
				_("Too many verification attempts. Please try again later"), frappe.RateLimitExceededError
			)


def normalize_recipients(email=None, phone=None):
	return (str(email or "").strip().lower() or None, str(phone or "").strip() or None)


def require_trusted_login_origin():
	"""Protect cookie login from browser login-CSRF, including the initial Guest request."""
	request = getattr(frappe.local, "request", None)
	if not request:
		return
	origin = request.headers.get("Origin")
	if not origin:
		if request.headers.get("Sec-Fetch-Site") == "cross-site":
			frappe.throw(_("Untrusted login origin"), frappe.PermissionError)
		return
	allowed = frappe.conf.get("allow_cors") or []
	if isinstance(allowed, str):
		allowed = [allowed]
	trusted = {str(value).rstrip("/") for value in allowed if value != "*"}
	trusted.add(f"{request.scheme}://{request.host}")
	if origin.rstrip("/") not in trusted:
		frappe.throw(_("Untrusted login origin"), frappe.PermissionError)
