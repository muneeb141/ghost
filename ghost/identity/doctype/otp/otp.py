# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import secrets
import string

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

from ghost.sender import send_otp


class OTP(Document):
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
			"name": ["!=", self.name],
		}
		if self.email:
			filters["email"] = self.email
		if self.phone:
			filters["phone"] = self.phone

		otps = frappe.get_all("OTP", filters=filters)

		for otp in otps:
			frappe.db.set_value("OTP", otp.name, "status", "Expired")


def generate(email=None, phone=None, purpose=None, user=None, send=True):
	settings = frappe.get_single("Ghost Settings")
	delivery_method = settings.otp_delivery_type or "Email"

	if delivery_method in ["Email", "Both"] and not email:
		frappe.throw(_(f"Email is required for {delivery_method} delivery method"))

	if delivery_method in ["SMS", "Both"] and not phone:
		frappe.throw(_(f"Phone is required for {delivery_method} delivery method"))

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
			"doctype": "OTP",
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
			if delivery_method in ["Email", "Both"]:
				email_result = send_otp(
					otp_code=otp_code,
					delivery_method="Email",
					email=email,
					phone=phone,
					otp_name=otp_doc.name,
				)
				if email_result:
					send_results.append(email_result)

			if delivery_method in ["SMS", "Both"]:
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
	otp_doc = None
	if email and frappe.db.exists(
		"OTP", {"otp_code": otp_code, "email": email, "status": "Valid", "purpose": purpose}
	):
		otp_doc = frappe.get_doc(
			"OTP",
			{"otp_code": otp_code, "email": email, "status": "Valid", "purpose": purpose},
		)
	elif phone and frappe.db.exists(
		"OTP", {"otp_code": otp_code, "phone": phone, "status": "Valid", "purpose": purpose}
	):
		otp_doc = frappe.get_doc(
			"OTP",
			{"otp_code": otp_code, "phone": phone, "status": "Valid", "purpose": purpose},
		)

	if not otp_doc:
		frappe.throw(_("Invalid OTP"))

	otp_doc.check_expiry()

	if otp_doc.status == "Expired":
		frappe.throw(_("OTP has expired"))

	otp_doc.status = "Expired"
	otp_doc.save(ignore_permissions=True)

	return {"valid": True}


def get_user_otps(user=None, phone=None, email=None):
	filters = {"creation": [">=", add_to_date(now_datetime(), hours=-1)]}
	if user:
		filters["user"] = user
	if phone:
		filters["phone"] = phone
	if email:
		filters["email"] = email
	return frappe.get_all("OTP", filters=filters)
