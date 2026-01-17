import frappe
from frappe import _

from frappe_identity.frappe_identity.doctype.otp.otp import generate as generate_otp
from frappe_identity.frappe_identity.doctype.otp.otp import verify as verify_otp


# API: POST /api/method/otp_generation.api.send_otp
@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_otp(email=None, phone=None, purpose=None, user=None):
	"""
	Send OTP API endpoint

	Args:
	    email: Email address (required for Email delivery)
	    phone: Phone number (required for SMS delivery)
	    purpose: Purpose of OTP (sign_up, reset_password, etc.)
	    user: User link (optional)

	Returns:
	    Standardized response with OTP code and name
	"""
	try:
		generate_otp(
			email=email,
			phone=phone,
			purpose=purpose,
			user=user,
		)
		frappe.local.response["http_status_code"] = 200
		frappe.local.response["message"] = _("OTP generated successfully")
		return frappe.local.response

	except frappe.ValidationError as e:
		frappe.local.response["http_status_code"] = 400
		frappe.local.response["message"] = str(e)
		return frappe.local.response

	except Exception as e:
		frappe.log_error(message=f"OTP Generation Error: {frappe.get_traceback()}", title="OTP Generation")
		frappe.local.response["http_status_code"] = 500
		frappe.local.response["message"] = _("Failed to generate OTP")
		frappe.local.response["error"] = e
		return frappe.local.response


# API: POST /api/method/otp_generation.api.validate_otp
@frappe.whitelist(allow_guest=True, methods=["POST"])
def validate_otp(otp_code, email=None, phone=None, purpose=None):
	"""
	Verify OTP API endpoint

	Args:
	    otp_code: The OTP code to verify
	    email: Email address (if verifying via email)
	    phone: Phone number (if verifying via phone)
	    purpose: Purpose of OTP (optional)

	Returns:
	    Standardized response indicating if OTP is valid
	"""
	try:
		if not otp_code:
			frappe.local.response["http_status_code"] = 400
			frappe.local.response["message"] = _("OTP code is required")
			return frappe.local.response
		if not email and not phone:
			frappe.local.response["http_status_code"] = 400
			frappe.local.response["message"] = _("Either email or phone must be provided")
			return frappe.local.response

		verify_otp(otp_code=otp_code, email=email, phone=phone, purpose=purpose)

		frappe.local.response["http_status_code"] = 200
		frappe.local.response["message"] = _("OTP verified successfully")
		return frappe.local.response

	except frappe.ValidationError as e:
		frappe.local.response["http_status_code"] = 400
		frappe.local.response["message"] = str(e)
		return frappe.local.response

	except Exception as e:
		frappe.log_error(
			message=f"OTP Verification Error: {frappe.get_traceback()}", title="OTP Verification"
		)
		frappe.local.response["http_status_code"] = 500
		frappe.local.response["message"] = _("OTP verification failed")
		frappe.local.response["error"] = e
		return frappe.local.response
