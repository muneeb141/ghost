import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

from ghost.api import user_details


class TestUserDetails(unittest.TestCase):
	def setUp(self):
		def raise_error(message, exception):
			raise exception(message)

		for patcher in (
			patch.object(frappe.local, "flags", SimpleNamespace(in_test=False), create=True),
			patch.object(user_details, "_", lambda message: message),
			patch.object(frappe, "throw", side_effect=raise_error),
		):
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_guest_cannot_read_or_update(self):
		with patch.object(frappe, "session", SimpleNamespace(user="Guest")):
			with self.assertRaises(frappe.AuthenticationError):
				user_details.get_user_details()
			with self.assertRaises(frappe.AuthenticationError):
				user_details.update_mobile_number("+911234567890", "123456")

	def test_profile_read_uses_only_session_user_and_public_fields(self):
		db = Mock()
		db.get_value.return_value = {"name": "owner@example.com", "email": "owner@example.com"}
		with patch.object(frappe, "session", SimpleNamespace(user="owner@example.com")):
			with patch.object(frappe, "db", db):
				result = user_details.get_user_details()

		self.assertTrue(result["success"])
		fields = db.get_value.call_args.args[2]
		self.assertEqual(db.get_value.call_args.args[:2], ("User", "owner@example.com"))
		self.assertNotIn("api_secret", fields)
		self.assertNotIn("password", fields)

	def test_mobile_update_requires_matching_otp_and_uses_session_user(self):
		db = Mock()
		db.get_value.return_value = None
		with patch.object(frappe, "session", SimpleNamespace(user="owner@example.com")):
			with patch.object(frappe, "db", db):
				with patch.object(user_details, "verify_otp") as verify:
					result = user_details.update_mobile_number(" +911234567890 ", "123456")

		verify.assert_called_once_with("123456", phone="+911234567890", purpose="Conversion")
		db.set_value.assert_called_once_with("User", "owner@example.com", "mobile_no", "+911234567890")
		self.assertEqual(result["user"], "owner@example.com")
		db.commit.assert_not_called()

	def test_mobile_number_owned_by_another_user_is_rejected(self):
		db = Mock()
		db.get_value.return_value = "other@example.com"
		with patch.object(frappe, "session", SimpleNamespace(user="owner@example.com")):
			with patch.object(frappe, "db", db):
				with patch.object(user_details, "verify_otp") as verify:
					with self.assertRaises(frappe.ValidationError):
						user_details.update_mobile_number("+911234567890", "123456")

		verify.assert_not_called()
		db.set_value.assert_not_called()

	def test_failed_otp_does_not_change_mobile_number(self):
		db = Mock()
		db.get_value.return_value = None
		with patch.object(frappe, "session", SimpleNamespace(user="owner@example.com")):
			with patch.object(frappe, "db", db):
				with patch.object(user_details, "verify_otp", side_effect=frappe.ValidationError("Invalid OTP")):
					with self.assertRaises(frappe.ValidationError):
						user_details.update_mobile_number("+911234567890", "bad-code")

		db.set_value.assert_not_called()
