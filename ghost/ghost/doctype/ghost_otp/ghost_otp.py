# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import hmac
import secrets
import string

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

from ghost.security import limit_verification, normalize_recipients, require_test_sandbox
from ghost.sender import send_otp


class GhostOTP(Document):
	def validate(self):
		if not self.expiry:
			self.set_expiry()
		self.check_expiry()

	def after_insert(self):
		self.expire_all_otps()

	def set_expiry(self):
		settings = frappe.get_single("Ghost Settings")
		expiry_minutes = settings.expiry_time_minutes or 10
		self.expiry = add_to_date(now_datetime(), minutes=expiry_minutes)

	def check_expiry(self):
		expiry_datetime = get_datetime(self.expiry)
		if expiry_datetime and get_datetime(now_datetime()) > expiry_datetime:
			self.status = "Expired"

	def expire_all_otps(self):
		filters = {
			"status": "Valid",
			"purpose": self.purpose,
			"name": ["!=", self.name],
		}
		if self.email:
			filters["email"] = self.email
		if self.phone:
			filters["phone"] = self.phone

		otps = frappe.get_all("Ghost OTP", filters=filters)

		for otp in otps:
			frappe.db.set_value("Ghost OTP", otp.name, "status", "Expired")


def generate(email=None, phone=None, purpose=None, user=None, send=True):
	email, phone = normalize_recipients(email, phone)
	settings = frappe.get_single("Ghost Settings")
	require_test_sandbox(settings)
	if bool(email) == bool(phone):
		frappe.throw(_("Provide exactly one OTP recipient: email or phone"))
	purpose = purpose or "Login"
	if purpose not in ("Login", "Conversion", "Sign Up", "Reset Password"):
		frappe.throw(_("Invalid OTP purpose"))
	delivery_method = settings.otp_delivery_type or "Email"
	if delivery_method == "Both":
		delivery_method = "Email" if email else "SMS"
	if (delivery_method == "Email" and not email) or (delivery_method == "SMS" and not phone):
		frappe.throw(_("The requested OTP delivery channel is not configured"))
	if delivery_method not in ("Email", "SMS"):
		frappe.throw(_("Configure an OTP delivery channel"))
	if getattr(settings, "sandbox_mode", 0):
		return {
			"otp_code": settings.sandbox_otp or "000141",
			"name": None,
			"sent": False,
			"send_results": [],
			"sandbox": True,
		}

	otp_length = settings.otp_length or 6
	otp_code_type = settings.otp_code_type or "Numeric"

	if otp_code_type == "Numeric":
		otp_code = str(secrets.randbelow(10**otp_length)).zfill(otp_length)
	else:
		characters = string.ascii_lowercase + string.digits
		otp_code = "".join(secrets.choice(characters) for _ in range(otp_length))

	user_otps = get_user_otps(user=user, phone=phone, email=email)
	if len(user_otps) >= settings.max_otp_attempts:
		frappe.throw(_("You have reached the maximum number of OTP attempts. Please try again after 1 hour."))

	otp_doc = frappe.get_doc(
		{
			"doctype": "Ghost OTP",
			"otp_code": otp_code,
			"email": email,
			"phone": phone,
			"purpose": purpose,
			"user": user,
			"delivery_method": delivery_method,
			"status": "Valid",
		}
	)

	otp_doc.insert(ignore_permissions=True)

	send_results = []
	if send:
		try:
			if delivery_method in ["Email", "Both"] and email:
				email_result = send_otp(
					otp_code=otp_code,
					delivery_method="Email",
					email=email,
					phone=phone,
					otp_name=otp_doc.name,
				)
				if email_result:
					send_results.append(email_result)

			if delivery_method in ["SMS", "Both"] and phone:
				sms_result = send_otp(
					otp_code=otp_code, delivery_method="SMS", email=email, phone=phone, otp_name=otp_doc.name
				)
				if sms_result:
					send_results.append(sms_result)
		except Exception:
			frappe.log_error(
				message=f"OTP generated but failed to send: {frappe.get_traceback()}", title="OTP Generation"
			)

	return {
		"otp_code": otp_code,
		"name": otp_doc.name,
		"sent": len(send_results) > 0,
		"send_results": send_results,
	}


def verify(otp_code, email=None, phone=None, purpose=None):
	"""Verify a recipient/purpose-bound code and consume it under a row lock."""
	email, phone = normalize_recipients(email, phone)
	settings = frappe.get_cached_doc("Ghost Settings")
	require_test_sandbox(settings)
	purpose = purpose or "Login"
	if (
		purpose not in ("Login", "Conversion", "Sign Up", "Reset Password")
		or bool(email) == bool(phone)
		or not otp_code
	):
		frappe.throw(_("OTP, recipient and a valid purpose are required"))
	identity = f"{email or ''}|{phone or ''}"
	limit_verification(identity, purpose, int(settings.max_otp_attempts or 5))
	if getattr(settings, "sandbox_mode", 0):
		if hmac.compare_digest(str(otp_code), str(settings.sandbox_otp or "000141")):
			return {"valid": True, "sandbox": True}
		frappe.throw(_("Invalid OTP"))
	filters = {"status": "Valid", "purpose": purpose}
	if email:
		filters["email"] = email
	if phone:
		filters["phone"] = phone
	name = frappe.db.get_value("Ghost OTP", filters, "name", order_by="creation desc")
	row = (
		frappe.db.get_value(
			"Ghost OTP",
			name,
			["name", "otp_code", "expiry", "status", "email", "phone", "purpose"],
			as_dict=True,
			for_update=True,
		)
		if name
		else None
	)
	if (
		not row
		or row.status != "Valid"
		or row.purpose != purpose
		or bool(row.email) == bool(row.phone)
		or (email and row.email != email)
		or (phone and row.phone != phone)
		or not hmac.compare_digest(str(row.otp_code), str(otp_code))
	):
		frappe.throw(_("Invalid OTP"))
	if get_datetime(row.expiry) <= get_datetime(now_datetime()):
		frappe.throw(_("OTP has expired"))
	frappe.db.set_value("Ghost OTP", row.name, "status", "Expired")
	return {"valid": True}


def get_user_otps(user=None, phone=None, email=None):
	filters = {"creation": [">=", add_to_date(now_datetime(), hours=-1)]}
	if user:
		filters["user"] = user
	if phone:
		filters["phone"] = phone
	if email:
		filters["email"] = email
	return frappe.get_all("Ghost OTP", filters=filters)


# Compatibility for imports and the pre-migration legacy DocType controller.
OTP = GhostOTP
