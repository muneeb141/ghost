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
		frappe.local.response = frappe._dict()
		send_otp(email=email, purpose="Sign Up")
		response = frappe.local.response
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
		frappe.local.response = frappe._dict()
		validate_otp(otp_code=code, email=email, purpose="Sign Up")
		response = frappe.local.response
		self.assertEqual(response.get("http_status_code"), 200)

		
		# 3. Verify Invalid OTP
		frappe.local.response = frappe._dict()
		validate_otp(otp_code="000000", email=email, purpose="Sign Up")
		response_bad = frappe.local.response
		self.assertNotEqual(response_bad.get("http_status_code"), 200)



		# 4. Cleanup
		frappe.delete_doc("OTP", otp_name)

	def tearDown(self):
		pass


class TestSandboxOTP(unittest.TestCase):
	"""Tests for Sandbox Mode: fixed OTP bypass, no DB interaction."""

	SANDBOX_OTP = "000141"

	def _enable_sandbox(self):
		# Use direct DB writes so this works even before bench migrate has
		# added the new columns to the test database schema.
		try:
			frappe.db.set_value("Ghost Settings", "Ghost Settings", "sandbox_mode", 1)
			frappe.db.set_value("Ghost Settings", "Ghost Settings", "sandbox_otp", self.SANDBOX_OTP)
			frappe.db.commit()
		except Exception:
			# If the column doesn't exist yet (pre-migrate), run migrate first.
			from frappe.migrate import migrate
			migrate()
			frappe.db.set_value("Ghost Settings", "Ghost Settings", "sandbox_mode", 1)
			frappe.db.set_value("Ghost Settings", "Ghost Settings", "sandbox_otp", self.SANDBOX_OTP)
			frappe.db.commit()
		# Bust cache so get_cached_doc picks up the change
		frappe.clear_cache(doctype="Ghost Settings")

	def _disable_sandbox(self):
		try:
			frappe.db.set_value("Ghost Settings", "Ghost Settings", "sandbox_mode", 0)
			frappe.db.commit()
		except Exception:
			pass
		frappe.clear_cache(doctype="Ghost Settings")

	def tearDown(self):
		# Always restore sandbox=off so other test classes are not affected.
		self._disable_sandbox()

	# ── Tests ────────────────────────────────────────────────────────────────

	def test_sandbox_generate_returns_fixed_otp(self):
		"""generate() must return the static sandbox OTP without touching the DB."""
		self._enable_sandbox()

		result = generate(email="qa@test.local", purpose="Login")

		self.assertTrue(result.get("sandbox"), "Response must include sandbox=True")
		self.assertEqual(result["otp_code"], self.SANDBOX_OTP)
		self.assertIsNone(result["name"], "No OTP DB record should be created in sandbox mode")
		self.assertFalse(result["sent"], "No delivery should occur in sandbox mode")

	def test_sandbox_verify_accepts_fixed_otp(self):
		"""verify() must accept the exact sandbox OTP and return valid=True."""
		self._enable_sandbox()

		result = verify(otp_code=self.SANDBOX_OTP, email="qa@test.local", purpose="Login")

		self.assertTrue(result.get("valid"))
		self.assertTrue(result.get("sandbox"), "Response must include sandbox=True")

	def test_sandbox_verify_rejects_wrong_otp(self):
		"""verify() must reject any OTP that is not the sandbox OTP."""
		self._enable_sandbox()

		with self.assertRaises(frappe.ValidationError):
			verify(otp_code="000000", email="qa@test.local", purpose="Login")
