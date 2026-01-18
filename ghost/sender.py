# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def send_otp(otp_code, delivery_method, email=None, phone=None, **kwargs):
	"""
	Send OTP using the configured sender from settings

	Args:
	    otp_code: The OTP code to send
	    delivery_method: "Email" or "SMS"
	    email: Email address (for Email delivery)
	    phone: Phone number (for SMS delivery)
	    **kwargs: Additional arguments to pass to sender function

	Returns:
	    dict: Result from sending or None if no sender configured
	"""
	settings = frappe.get_single("Ghost Settings")

	if delivery_method == "Email":
		return send_otp_email(otp_code, email, settings, **kwargs)
	elif delivery_method == "SMS":
		return send_otp_sms(otp_code, phone, settings, **kwargs)

	return None


def send_otp_email(otp_code, email, settings, **kwargs):
	"""Send OTP via email using Frappe's sendmail with Email Template"""
	if not settings.email_account or not settings.email_template:
		return None

	try:
		email_account = frappe.get_doc("Email Account", settings.email_account)
		email_template = frappe.get_doc("Email Template", settings.email_template)

		doc = {"otp_code": otp_code, **kwargs}

		subject = email_template.get_formatted_subject(doc)
		message = email_template.get_formatted_response(doc)

		frappe.sendmail(
			recipients=[email], sender=email_account.email_id, subject=subject, message=message, delayed=False
		)

		return {"status": "sent", "method": "email"}

	except Exception as e:
		print(e)
		frappe.log_error(message=f"Error sending OTP email: {frappe.get_traceback()}", title="OTP Sender")
		raise


def send_otp_sms(otp_code, phone, settings, **kwargs):
	"""Send OTP via SMS using configured sender function"""
	if not settings.sms_sender:
		return None

	try:
		sender_func = frappe.get_attr(settings.sms_sender)
		result = sender_func(otp_code=otp_code, phone=phone, **kwargs)

		return {"status": "sent", "method": "sms", "result": str(result)}
	except AttributeError:
		frappe.log_error(
			message=f"Failed to load SMS sender function '{settings.sms_sender}'", title="OTP Sender"
		)
		raise frappe.ValidationError(_(f"Failed to load SMS sender function: {settings.sms_sender}"))
	except Exception:
		frappe.log_error(message=f"Error sending OTP SMS: {frappe.get_traceback()}", title="OTP Sender")
		raise
