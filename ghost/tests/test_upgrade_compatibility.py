"""Existing-site migration assertions; full previous-release installs also run in CI."""

import uuid
from unittest.mock import patch

import frappe

from ghost.patches.v1_0.set_ghost_settings_defaults import execute
from ghost.tests.helpers import GhostIntegrationCase


class TestUpgradeCompatibility(GhostIntegrationCase):
	def test_migration_preserves_existing_otp_and_is_idempotent(self):
		code = self.code()
		name = frappe.db.get_value("OTP", {"email": self.email, "status": "Valid"}, "name")
		with patch("builtins.print"):
			execute()
			first = frappe.get_single("Ghost Settings").as_dict()
			execute()
		second = frappe.get_single("Ghost Settings").as_dict()
		self.assertEqual(first, second)
		self.assertEqual(frappe.db.get_value("OTP", name, "otp_code"), code)
		self.assertEqual(frappe.get_meta("OTP").module, "Ghost")
		self.assertEqual(frappe.get_single("Ghost Settings").client_id, self.client.name)
		self.assertTrue(frappe.get_single("Ghost Settings").enable_otp_login)

	def test_legacy_security_settings_are_upgraded_without_removing_users(self):
		source = self.new_ghost()["user"]
		for field in ("verify_otp_on_conversion", "invalidate_ghost_tokens_on_conversion"):
			frappe.db.set_single_value("Ghost Settings", field, 0)
		frappe.db.set_single_value("Ghost Settings", "sandbox_mode", 1)
		with patch.dict(frappe.flags, {"in_test": False}), patch("builtins.print"):
			execute()
		settings = frappe.get_single("Ghost Settings")
		self.assertTrue(settings.verify_otp_on_conversion)
		self.assertTrue(settings.invalidate_ghost_tokens_on_conversion)
		self.assertFalse(settings.sandbox_mode)
		self.assertTrue(frappe.db.exists("User", source))

	def test_legacy_eight_character_identity_preserves_native_user_links(self):
		source = f"ghost_{uuid.uuid4().hex[:8]}@{self.settings.ghost_email_domain}"
		self.new_user(source, role="Ghost")
		lead = frappe.get_doc(
			{
				"doctype": "Ghost Lead",
				"ghost_email": source,
				"captured_email": self.email,
				"status": "Captured",
			}
		).insert(ignore_permissions=True)
		result = self.convert(source)
		self.assertEqual(result["user"], self.email)
		self.assertEqual(frappe.db.get_value("Ghost Lead", lead.name, "ghost_email"), self.email)

	def test_custom_domain_case_does_not_break_existing_anonymous_owners(self):
		source = self.new_ghost()["user"]
		self.configure(ghost_email_domain=self.settings.ghost_email_domain.upper())
		result = self.convert(source)
		self.assertEqual(result["user"], self.email)
