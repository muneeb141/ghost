import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from ghost.ghost.doctype.ghost_otp.ghost_otp import generate as generate_otp
from ghost.ghost.doctype.ghost_otp.ghost_otp import verify as verify_otp
from ghost.security import normalize_recipients


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=300)
def send_otp(
	email: str | None = None, phone: str | None = None, purpose: str | None = None, user: str | None = None
):
	"""Deliver a code; never expose codes, record IDs or transport details to the caller."""
	email, phone = normalize_recipients(email, phone)
	if not (email or phone) or purpose not in (None, "Login", "Conversion", "Sign Up", "Reset Password"):
		frappe.throw(_("A recipient and valid OTP purpose are required"))
	if user and (frappe.session.user == "Guest" or user != frappe.session.user):
		frappe.throw(_("OTP user must be the authenticated caller"), frappe.PermissionError)
	result = generate_otp(email=email, phone=phone, purpose=purpose, user=user)
	if not result.get("sent"):
		frappe.throw(_("Could not deliver the verification code. Please try again later"))
	return {"status": "success", "message": _("Verification code sent")}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=300)
def validate_otp(
	otp_code: str, email: str | None = None, phone: str | None = None, purpose: str | None = None
):
	"""Consume a code without starting a login; auth clients should call auth.login directly."""
	verify_otp(otp_code=otp_code, email=email, phone=phone, purpose=purpose)
	return {"status": "success", "message": _("OTP verified successfully")}
