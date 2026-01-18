import frappe
import unittest
from ghost.ghost.doctype.otp.otp import generate, verify
from ghost.api.otp import send_otp, validate_otp

class TestFrappeIdentityOTP(unittest.TestCase):
	def setUp(self):
		settings = frappe.get_single("Ghost Settings")
		settings.max_otp_attempts = 5
		settings.otp_delivery_type = "Email"
		settings.otp_code_type = "Numeric"
		settings.otp_length = 6
		settings.save()

	def test_otp_flow(self):
		email = "test_otp@guest.local"
		


		# 1. Send OTP
		response = send_otp(email=email, purpose="Sign Up")
		if response.get("http_status_code") != 200:
			print(f"\n[DEBUG] Send OTP Failed: {response.get('message')} - {response.get('error')}")
		self.assertEqual(response.get("http_status_code"), 200, f"Send OTP Failed: {response.get('message')}")

		
		# Find the OTP
		otp_name = frappe.db.get_value("OTP", {"email": email, "status": "Valid"}, "name")
		self.assertTrue(otp_name, "OTP Document should be created")

		otp_doc = frappe.get_doc("OTP", otp_name)
		code = otp_doc.otp_code
		
		# 2. Verify Valid OTP
		# Note: validate_otp calls verify_otp which might raise exceptions or return None.
		# The API wrapper returns a dict.
		response = validate_otp(otp_code=code, email=email, purpose="Sign Up")
		self.assertEqual(response.get("http_status_code"), 200)
		
		# 3. Verify Invalid OTP
		response_bad = validate_otp(otp_code="000000", email=email, purpose="Sign Up")
		self.assertNotEqual(response_bad.get("http_status_code"), 200)

		# 4. Cleanup
		frappe.delete_doc("OTP", otp_name)

	def tearDown(self):
		pass
