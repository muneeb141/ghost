import re

import frappe

from ghost.api.ghost import convert_to_real_user
from ghost.tests.helpers import GhostIntegrationCase


class TestFrappeIdentityAPI(GhostIntegrationCase):
	def test_create_ghost_session(self):
		data = self.new_ghost()
		self.assertRegex(
			data["user"], rf"^ghost_[0-9a-f]{{32}}@{re.escape(self.settings.ghost_email_domain)}$"
		)
		self.assertEqual(frappe.db.get_value("User", data["user"], "user_type"), "Website User")
		self.assertIn(self.settings.ghost_role, frappe.get_roles(data["user"]))
		self.assertTrue(data["access_token"])

	def test_creation_is_disabled_by_settings(self):
		self.configure(enable_ghost_feature=0)
		with self.assertRaises(frappe.ValidationError):
			self.new_ghost()

	def test_caller_selected_existing_and_new_emails_are_rejected(self):
		self.new_user()
		for email in (self.email, "new-" + self.email):
			with self.subTest(email=email), self.assertRaises(frappe.PermissionError):
				self.new_ghost(email=email)

	def test_convert_to_real_user(self):
		source = self.new_ghost()["user"]
		result = self.convert(source, first_name="Real", last_name="Person")
		self.assertEqual(result["conversion_mode"], "rename")
		self.assertFalse(frappe.db.exists("User", source))
		user = frappe.get_doc("User", self.email)
		self.assertEqual(user.first_name, "Real")
		self.assertEqual(user.user_type, "Website User")
		self.assertNotIn(self.settings.ghost_role, [r.role for r in user.roles])

	def test_convert_existing_user_manual_migration(self):
		target = self.new_user()
		source = self.new_ghost()["user"]
		from ghost.ghost.doctype.ghost_otp.ghost_otp import generate

		linked = generate(email="linked-" + self.email, user=source, purpose="Login", send=False)
		result = self.convert(source, first_name="Unwanted replacement")
		self.assertEqual(result["conversion_mode"], "manual_migration")
		self.assertEqual(frappe.db.get_value("User", target.name, "first_name"), "Fixture")
		self.assertEqual(frappe.db.get_value("Ghost OTP", linked["name"], "user"), target.name)
		self.assertEqual(frappe.db.get_value("User", source, "enabled"), 0)

	def test_convert_requires_otp_even_for_legacy_setting(self):
		source = self.new_ghost()["user"]
		frappe.db.set_single_value("Ghost Settings", "verify_otp_on_conversion", 0)
		with self.actor(source), self.assertRaises(frappe.ValidationError):
			convert_to_real_user(source, self.email)

	def test_convert_with_invalid_otp(self):
		source = self.new_ghost()["user"]
		with self.actor(source), self.assertRaises(frappe.ValidationError):
			convert_to_real_user(source, self.email, otp_code="wrong")
		self.assertFalse(frappe.db.exists("User", self.email))

	def test_conversion_revokes_ghost_tokens_and_mints_new_tokens(self):
		data = self.new_ghost()
		result = self.convert(data["user"])
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", data["access_token"], "status"), "Revoked")
		self.assertEqual(
			frappe.db.get_value("OAuth Bearer Token", result["access_token"], "user"), self.email
		)

	def test_role_transition(self):
		role = f"Ghost Verified {self.tag[:10]}"
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert()
		self.configure(default_user_role=role)
		source = self.new_ghost()["user"]
		self.convert(source)
		self.assertIn(role, frappe.get_roles(self.email))
		self.assertEqual(frappe.db.get_value("User", self.email, "user_type"), "Website User")

	def test_native_rename_preserves_user_link_in_lead(self):
		self.configure(enable_lead_capture=1)
		source = self.new_ghost()["user"]
		from ghost.api.lead import capture_email

		with self.actor(source):
			capture_email(self.email)
		name = frappe.db.get_value("Ghost Lead", {"ghost_email": source}, "name")
		self.convert(source)
		self.assertEqual(frappe.db.get_value("Ghost Lead", name, "ghost_email"), self.email)
		self.assertEqual(frappe.db.get_value("Ghost Lead", name, "status"), "Converted")

	def test_public_desk_role_conversion_is_denied_before_rename_or_revocation(self):
		data = self.new_ghost()
		self.configure(allow_system_user_login=1, default_user_role="System Manager")
		with self.assertRaises(frappe.PermissionError):
			self.convert(data["user"])
		self.assertTrue(frappe.db.exists("User", data["user"]))
		self.assertFalse(frappe.db.exists("User", self.email))
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", data["access_token"], "status"), "Active")
