from unittest.mock import patch

import frappe

from ghost.api.ghost import convert_to_real_user
from ghost.api.lead import capture_email
from ghost.ghost.doctype.ghost_otp.ghost_otp import generate
from ghost.tests.helpers import GhostIntegrationCase


class TestMultiDeviceMerge(GhostIntegrationCase):
	def assert_unverified_related_account_is_untouched(self, enabled):
		self.configure(enable_multi_device_merge=enabled, merge_detection_method="Lead Email")
		a = self.new_ghost()["user"]
		b = self.new_ghost()["user"]
		with patch("ghost.api.merge.find_related_ghosts", return_value=[b]) as find:
			result = self.convert(a)
		find.assert_not_called()
		self.assertNotIn("merged_ghosts", result)
		self.assertEqual(frappe.db.get_value("User", b, "enabled"), 1)

	def test_email_matching_does_not_claim_another_device(self):
		self.assert_unverified_related_account_is_untouched(1)

	def test_merge_disabled(self):
		self.assert_unverified_related_account_is_untouched(0)

	def test_two_owned_devices_join_one_verified_account_without_claiming_a_third(self):
		self.new_user()
		roles = set(frappe.get_roles(self.email))
		self.configure(enable_multi_device_merge=1, enable_lead_capture=1)
		devices = [self.new_ghost() for _ in range(3)]
		leads = []
		for device in devices:
			with self.actor(device["user"]):
				capture_email(self.email)
			leads.append(frappe.db.get_value("Ghost Lead", {"ghost_email": device["user"]}, "name"))
		for device in devices[:2]:
			linked = generate(email="linked-" + device["user"], user=device["user"], send=False)
			result = self.convert(device["user"])
			self.assertEqual(result["user"], self.email)
			self.assertEqual(frappe.db.get_value("Ghost OTP", linked["name"], "user"), self.email)
			self.assertEqual(frappe.db.get_value("User", device["user"], "enabled"), 0)
			self.assertEqual(
				frappe.db.get_value("OAuth Bearer Token", device["access_token"], "status"), "Revoked"
			)
		self.assertEqual(set(frappe.get_roles(self.email)), roles)
		self.assertEqual(frappe.db.count("User", {"email": self.email}), 1)
		self.assertEqual(
			[frappe.db.get_value("Ghost Lead", name, "status") for name in leads],
			["Converted", "Converted", "Captured"],
		)
		self.assertEqual(frappe.db.get_value("User", devices[2]["user"], "enabled"), 1)
		self.assertEqual(
			frappe.db.get_value("OAuth Bearer Token", devices[2]["access_token"], "status"), "Active"
		)

	def test_verified_target_does_not_authorize_an_unowned_matching_source(self):
		self.new_user()
		self.configure(enable_multi_device_merge=1, enable_lead_capture=1)
		a, b = self.new_ghost(), self.new_ghost()
		for device in (a, b):
			with self.actor(device["user"]):
				capture_email(self.email)
		code = self.code(purpose="Conversion")
		with self.actor(a["user"]):
			with self.assertRaises(frappe.PermissionError):
				convert_to_real_user(b["user"], self.email, otp_code=code)
			# The ownership failure did not consume the proof for the caller's own conversion.
			self.assertEqual(convert_to_real_user(a["user"], self.email, otp_code=code)["user"], self.email)
		self.assertEqual(frappe.db.get_value("User", b["user"], "enabled"), 1)
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", b["access_token"], "status"), "Active")
