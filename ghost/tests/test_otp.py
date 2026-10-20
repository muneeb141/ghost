from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from ghost.api.auth import login
from ghost.api.otp import send_otp, validate_otp
from ghost.ghost.doctype.otp.otp import generate, verify
from ghost.tests.helpers import GhostIntegrationCase


class TestFrappeIdentityOTP(GhostIntegrationCase):
	def test_otp_flow(self):
		with patch("ghost.ghost.doctype.otp.otp.send_otp", return_value={"status": "sent"}):
			response = send_otp(email=self.email, purpose="Sign Up")
		self.assertEqual(set(response), {"status", "message"})
		name = frappe.db.get_value("OTP", {"email": self.email, "purpose": "Sign Up"}, "name")
		code = frappe.db.get_value("OTP", name, "otp_code")
		self.assertEqual(validate_otp(code, email=self.email, purpose="Sign Up")["status"], "success")
		with self.assertRaises(frappe.ValidationError):
			validate_otp(code, email=self.email, purpose="Sign Up")

	def test_purposes_do_not_expire_each_other(self):
		login_code = self.code()
		conversion_code = self.code(purpose="Conversion")
		self.assertTrue(verify(login_code, email=self.email)["valid"])
		self.assertTrue(verify(conversion_code, email=self.email, purpose="Conversion")["valid"])

	def test_resend_invalidates_previous_code_of_same_purpose(self):
		self.code()
		latest = self.code()
		self.assertEqual(
			frappe.db.count("OTP", {"email": self.email, "purpose": "Login", "status": "Valid"}), 1
		)
		self.assertTrue(verify(latest, email=self.email)["valid"])

	def test_combined_email_phone_auth_challenge_is_rejected(self):
		self.configure(otp_delivery_type="Both")
		with self.assertRaises(frappe.ValidationError):
			generate(email=self.email, phone="+910000000001", purpose="Login", send=False)

	def test_legacy_combined_challenge_cannot_prove_email_only(self):
		self.new_user()
		code = self.code()
		name = frappe.db.get_value(
			"OTP", {"email": self.email, "purpose": "Login", "status": "Valid"}, "name"
		)
		frappe.db.set_value("OTP", name, "phone", "+910000000001")
		with self.actor("Guest"), self.assertRaises(frappe.ValidationError):
			login(code, email=self.email)

	def test_both_delivery_setting_selects_the_one_requested_recipient(self):
		self.configure(otp_delivery_type="Both")
		result = generate(email=self.email, purpose="Login", send=False)
		self.assertEqual(frappe.db.get_value("OTP", result["name"], "delivery_method"), "Email")

	def test_expired_codes_are_not_accepted(self):
		code = self.code()
		name = frappe.db.get_value("OTP", {"email": self.email, "status": "Valid"}, "name")
		frappe.db.set_value("OTP", name, "expiry", add_to_date(now_datetime(), minutes=-1))
		with self.assertRaises(frappe.ValidationError):
			verify(code, email=self.email)


class TestSandboxOTP(GhostIntegrationCase):
	def test_sandbox_generate_returns_fixed_otp(self):
		self.configure(sandbox_mode=1, sandbox_otp="000141")
		result = generate(email=self.email)
		self.assertEqual(result["otp_code"], "000141")
		self.assertIsNone(result["name"])
		self.assertFalse(result["sent"])

	def test_sandbox_verify_accepts_fixed_otp(self):
		self.configure(sandbox_mode=1, sandbox_otp="000141")
		self.assertTrue(verify("000141", email=self.email)["sandbox"])

	def test_sandbox_verify_rejects_wrong_otp(self):
		self.configure(sandbox_mode=1, sandbox_otp="000141")
		with self.assertRaises(frappe.ValidationError):
			verify("wrong", email=self.email)

	def test_production_rejects_a_saved_sandbox_configuration(self):
		self.configure(sandbox_mode=1, sandbox_otp="000141")
		with patch.dict(frappe.flags, {"in_test": False}), self.assertRaises(frappe.PermissionError):
			generate(email=self.email)
