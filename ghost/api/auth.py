import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, now_datetime

from ghost.ghost.doctype.otp.otp import verify as ghost_verify_otp
from ghost.security import (
	normalize_recipients,
	require_enabled_user,
	require_owned_ghost,
	require_trusted_login_origin,
)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=300)
def login(otp, email=None, mobile_no=None, first_name=None, last_name=None, client_id=None):
	"""Passwordless login/signup using a recipient-bound Login OTP."""
	require_trusted_login_origin()
	email, mobile_no = normalize_recipients(email, mobile_no)
	if bool(email) == bool(mobile_no):
		frappe.throw(_("Provide exactly one email address or mobile number"))
	settings = frappe.get_single("Ghost Settings")
	if not settings.get("enable_otp_login"):
		frappe.throw(_("OTP login is disabled"), frappe.PermissionError)
	if client_id and client_id != settings.client_id:
		frappe.throw(_("OAuth client does not match Ghost Settings"), frappe.PermissionError)
	actor = frappe.session.user
	is_ghost = bool(actor and actor.startswith("ghost_"))
	if is_ghost:
		require_owned_ghost(actor)
	ghost_verify_otp(otp_code=otp, email=email, phone=mobile_no, purpose="Login")
	if is_ghost:
		from ghost.api.ghost import _convert_verified_user

		user = email or f"{mobile_no}@mobile.login"
		_convert_verified_user(actor, user, first_name, last_name, issue_tokens=False)
	else:
		filters = {"email": email} if email else {"mobile_no": mobile_no}
		user = frappe.db.get_value("User", filters, "name")
		if not user:
			user = create_new_user(
				email or f"{mobile_no}@mobile.login", mobile_no, first_name or "User", last_name
			)
	require_enabled_user(user)
	if getattr(frappe.local, "request", None):
		from frappe.auth import LoginManager

		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(user)
	response = {"status": "success", "message": _("Logged In"), "user": user}
	# Same-origin portals need only the HttpOnly Frappe session. Tokens are opt-in.
	if client_id:
		response.update(generate_oauth_tokens(user, client_id))
	return response


def create_new_user(email, mobile_no=None, first_name="User", last_name=None):
	settings = frappe.get_single("Ghost Settings")
	if not settings.get("allow_public_signup"):
		frappe.throw(_("Public signup is disabled"), frappe.PermissionError)
	default_role = settings.default_user_role
	if (
		default_role
		and frappe.db.get_value("Role", default_role, "desk_access")
		and not settings.get("allow_system_user_login")
	):
		frappe.throw(_("System user OTP login must be explicitly enabled"), frappe.PermissionError)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"mobile_no": mobile_no,
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": default_role}] if default_role else [],
		}
	)
	user.insert(ignore_permissions=True)
	return user.name


def generate_oauth_tokens(user, client_id=None):
	"""Private credential issuer; the caller must first prove identity ownership."""
	require_enabled_user(user)
	settings = frappe.get_single("Ghost Settings")
	if client_id and client_id != settings.client_id:
		frappe.throw(_("OAuth client does not match Ghost Settings"), frappe.PermissionError)
	client_id = settings.client_id
	if not client_id or not frappe.db.exists("OAuth Client", client_id):
		frappe.throw(_("Configure a valid OAuth Client in Ghost Settings"))
	seconds = int(settings.access_token_expiry_seconds or 3600)
	bearer_token = frappe.get_doc(
		{
			"doctype": "OAuth Bearer Token",
			"client": client_id,
			"user": user,
			"scopes": settings.ghost_token_scope or "all",
			"status": "Active",
			"expires_in": seconds,
			"expiration_time": add_to_date(now_datetime(), seconds=seconds),
			"access_token": frappe.generate_hash(length=40),
			"refresh_token": frappe.generate_hash(length=40),
		}
	)
	bearer_token.insert(ignore_permissions=True)
	# Frappe commits the successful request. Never commit half of an auth/conversion.
	return {
		"access_token": bearer_token.access_token,
		"refresh_token": bearer_token.refresh_token,
		"expires_in": seconds,
		"token_type": "Bearer",
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=300)
def refresh_bearer_token(refresh_token):
	if not refresh_token:
		frappe.throw(_("Refresh token is required"), frappe.AuthenticationError)
	# Resolve without a range lock, then lock the primary key and recheck live status.
	# Locking an unindexed refresh-token scan can deadlock against replacement inserts.
	name = frappe.db.get_value("OAuth Bearer Token", {"refresh_token": refresh_token}, "name")
	token = (
		frappe.db.get_value(
			"OAuth Bearer Token",
			name,
			["name", "user", "client", "creation", "status", "refresh_token"],
			as_dict=True,
			for_update=True,
		)
		if name
		else None
	)
	if not token or token.status != "Active" or token.refresh_token != refresh_token:
		frappe.throw(_("Invalid or expired refresh token"), frappe.AuthenticationError)
	settings = frappe.get_single("Ghost Settings")
	expires_on = add_to_date(token.creation, days=int(settings.refresh_token_expiry_days or 30))
	if now_datetime() >= expires_on:
		frappe.throw(_("Refresh token has expired. Please login again"), frappe.AuthenticationError)
	require_enabled_user(token.user)
	frappe.db.set_value("OAuth Bearer Token", token.name, "status", "Revoked")
	new_tokens = generate_oauth_tokens(token.user, token.client)
	return {
		"status": "success",
		"message": _("Token refreshed successfully"),
		"user": token.user,
		**new_tokens,
	}
