import frappe
from frappe import _

from ghost.ghost.doctype.otp.otp import verify as verify_otp


def _current_user():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required"), frappe.AuthenticationError)
	return user


@frappe.whitelist(methods=["POST"])
def update_mobile_number(mobile_no=None, otp_code=None):
	"""Set the signed-in user's mobile number after verifying that number by OTP."""
	user = _current_user()
	mobile_no = str(mobile_no or "").strip()
	if not mobile_no or not otp_code:
		frappe.throw(_("Mobile number and OTP code are required"), frappe.ValidationError)

	existing_owner = frappe.db.get_value("User", {"mobile_no": mobile_no}, "name")
	if existing_owner and existing_owner != user:
		frappe.throw(
			_("This mobile number is already associated with another account"), frappe.ValidationError
		)

	verify_otp(otp_code, phone=mobile_no, purpose="Conversion")
	frappe.db.set_value("User", user, "mobile_no", mobile_no)
	return {"success": True, "user": user, "mobile_no": mobile_no}


@frappe.whitelist(methods=["GET"])
def get_user_details():
	"""Return a small allowlist of profile fields for the signed-in user."""
	user = _current_user()
	details = frappe.db.get_value(
		"User",
		user,
		["name", "email", "mobile_no", "first_name", "last_name", "full_name", "user_image"],
		as_dict=True,
	)
	if not details:
		frappe.throw(_("User not found"), frappe.AuthenticationError)
	return {"success": True, **details}
