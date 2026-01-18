# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class OTPSettings(Document):
	def validate(self):
		if self.expiry_time_minutes and self.expiry_time_minutes < 1:
			frappe.throw(_("Expiry time must be at least 1 minute"))

		if self.otp_length and self.otp_length < 4:
			frappe.throw(_("OTP length must be at least 4 digits"))

		if self.otp_length and self.otp_length > 10:
			frappe.throw(_("OTP length cannot exceed 10 digits"))

		if self.otp_delivery_type in ["Email", "Both"]:
			self.validate_email_configuration()

		if self.otp_delivery_type in ["SMS", "Both"]:
			self.validate_sms_configuration()

	def validate_email_configuration(self):
		"""Validate email account and template are configured"""
		if not self.email_account:
			frappe.throw(_("Email Account is required when OTP Delivery Type is Email or Both"))

		if not self.email_template:
			frappe.throw(_("Email Template is required when OTP Delivery Type is Email or Both"))

		email_account = frappe.get_doc("Email Account", self.email_account)

		if not email_account.enable_outgoing:
			frappe.throw(_(f"Email Account '{self.email_account}' does not have outgoing enabled"))

		if not frappe.db.exists("Email Template", self.email_template):
			frappe.throw(_(f"Email Template '{self.email_template}' does not exist"))

	def validate_sms_configuration(self):
		"""Validate SMS sender function is configured"""
		if not self.sms_sender:
			frappe.throw(_("SMS Sender Function is required when OTP Delivery Type is SMS or Both"))

		try:
			func = frappe.get_attr(self.sms_sender)
			if not callable(func):
				frappe.throw(_(f"SMS sender function '{self.sms_sender}' is not callable"))
		except AttributeError:
			frappe.throw(_(f"SMS sender function '{self.sms_sender}' not found"))
		except Exception as e:
			frappe.throw(_(f"Error validating SMS sender function '{self.sms_sender}': {e}"))
