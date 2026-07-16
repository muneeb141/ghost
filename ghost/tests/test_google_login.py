import unittest
from unittest.mock import patch

import frappe

from ghost.api import auth as auth_module
from ghost.api.auth import google_login


class TestGoogleLogin(unittest.TestCase):
	def setUp(self):
		settings = frappe.get_single("Ghost Settings")
		settings.default_user_role = "Customer"
		settings.save()

		if not frappe.db.exists("Role", "Customer"):
			frappe.get_doc({"doctype": "Role", "role_name": "Customer"}).insert(
				ignore_permissions=True
			)
		frappe.set_user("Administrator")

	def _claims(self, email, **overrides):
		claims = {
			"iss": "https://accounts.google.com",
			"email": email,
			"email_verified": True,
			"given_name": "Goo",
			"family_name": "Gler",
		}
		claims.update(overrides)
		return claims

	def _delete_user(self, email):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)

	@patch("ghost.api.auth._verify_google_id_token")
	def test_new_user_signup_gets_default_role(self, mock_verify):
		email = "google_new@example.com"
		self._delete_user(email)
		mock_verify.return_value = self._claims(email)

		frappe.session.user = "Guest"
		resp = google_login(id_token="fake-token")

		self.assertEqual(resp["status"], "success")
		self.assertEqual(resp["user"], email)
		self.assertTrue(resp["is_new_user"])

		user = frappe.get_doc("User", email)
		self.assertEqual(user.first_name, "Goo")
		self.assertIn(
			"Customer",
			[r.role for r in user.roles],
			"New Google user should inherit the default role from Ghost Settings",
		)

	@patch("ghost.api.auth._verify_google_id_token")
	def test_existing_user_login_no_duplicate(self, mock_verify):
		email = "google_existing@example.com"
		if not frappe.db.exists("User", email):
			u = frappe.new_doc("User")
			u.email = email
			u.first_name = "Existing"
			u.save(ignore_permissions=True)
		mock_verify.return_value = self._claims(email, given_name="Existing")

		resp = google_login(id_token="fake-token")

		self.assertEqual(resp["user"], email)
		self.assertFalse(resp["is_new_user"])
		self.assertEqual(
			frappe.db.count("User", {"email": email}), 1, "Must not create a duplicate account"
		)

	@patch("ghost.api.auth._verify_google_id_token")
	def test_unverified_email_is_rejected(self, mock_verify):
		email = "google_unverified@example.com"
		self._delete_user(email)
		mock_verify.return_value = self._claims(email, email_verified=False)

		with self.assertRaises(frappe.AuthenticationError):
			google_login(id_token="fake-token")
		self.assertFalse(
			frappe.db.exists("User", email), "No user should be created for an unverified email"
		)

	@patch("ghost.api.auth._verify_google_id_token")
	def test_invalid_token_creates_no_user(self, mock_verify):
		# Simulates google-auth rejecting a wrong-audience / tampered token.
		email = "google_badtoken@example.com"
		self._delete_user(email)
		mock_verify.side_effect = frappe.AuthenticationError("Invalid Google token")

		with self.assertRaises(frappe.AuthenticationError):
			google_login(id_token="tampered-token")
		self.assertFalse(frappe.db.exists("User", email))

	def test_audience_is_pinned_to_configured_client_id(self):
		# The single check that stops token replay: verify_oauth2_token must be
		# called with audience == our configured client id.
		frappe.local.conf["google_web_client_id"] = "test-client.apps.googleusercontent.com"
		with patch("google.oauth2.id_token.verify_oauth2_token") as mock_v:
			mock_v.return_value = {"email": "x@example.com"}
			auth_module._verify_google_id_token("some-token")
			_, kwargs = mock_v.call_args
			self.assertEqual(kwargs.get("audience"), "test-client.apps.googleusercontent.com")

	def tearDown(self):
		frappe.set_user("Administrator")
