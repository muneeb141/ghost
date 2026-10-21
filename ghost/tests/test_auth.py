import frappe
from frappe.utils import add_to_date, now_datetime

from ghost.api.auth import generate_oauth_tokens, login, refresh_bearer_token
from ghost.tests.helpers import GhostIntegrationCase


class TestGhostAuth(GhostIntegrationCase):
	def test_direct_signup_and_login(self):
		code = self.code()
		with self.actor("Guest"):
			result = login(code, email=self.email, first_name="Verified", last_name="Person")
		user = frappe.get_doc("User", result["user"])
		self.assertEqual(user.first_name, "Verified")
		self.assertEqual(user.user_type, "Website User")
		self.assertNotIn("access_token", result)

	def test_existing_account_email_login(self):
		self.new_user()
		code = self.code()
		with self.actor("Guest"):
			self.assertEqual(login(code, email=self.email)["user"], self.email)
		self.assertEqual(frappe.db.count("User", {"email": self.email}), 1)

	def test_client_id_token_generation(self):
		self.new_user()
		code = self.code()
		with self.actor("Guest"):
			result = login(code, email=self.email, client_id=self.client.name)
		self.assertEqual(
			frappe.db.get_value("OAuth Bearer Token", result["access_token"], "user"), self.email
		)
		self.assertEqual(frappe.db.count("OAuth Bearer Token", {"user": self.email, "status": "Active"}), 1)

	def test_cookie_conversion_does_not_leave_orphan_bearer_credentials(self):
		source = self.new_ghost()["user"]
		code = self.code()
		with self.actor(source):
			result = login(code, email=self.email)
		self.assertEqual(result["user"], self.email)
		self.assertEqual(frappe.db.count("OAuth Bearer Token", {"user": self.email, "status": "Active"}), 0)

	def test_ghost_conversion_issues_only_the_requested_token_pair(self):
		source = self.new_ghost()["user"]
		code = self.code()
		with self.actor(source):
			result = login(code, email=self.email, client_id=self.client.name)
		self.assertTrue(result["access_token"])
		self.assertEqual(frappe.db.count("OAuth Bearer Token", {"user": self.email, "status": "Active"}), 1)

	def test_wrong_oauth_client_is_denied(self):
		with self.actor("Guest"), self.assertRaises(frappe.PermissionError):
			login("not-used", email=self.email, client_id="unconfigured")

	def test_refresh_bearer_token_returns_user(self):
		self.new_user()
		tokens = generate_oauth_tokens(self.email, self.client.name)
		result = refresh_bearer_token(tokens["refresh_token"])
		self.assertEqual(result["user"], self.email)
		self.assertNotEqual(tokens["refresh_token"], result["refresh_token"])

	def test_refresh_expiry_is_checked_at_exact_boundary(self):
		self.new_user()
		tokens = generate_oauth_tokens(self.email)
		frappe.db.set_value(
			"OAuth Bearer Token", tokens["access_token"], "creation", add_to_date(now_datetime(), days=-31)
		)
		with self.assertRaises(frappe.AuthenticationError):
			refresh_bearer_token(tokens["refresh_token"])

	def test_signup_policy_does_not_block_existing_account_login(self):
		self.new_user()
		self.configure(allow_public_signup=0)
		code = self.code()
		with self.actor("Guest"):
			self.assertEqual(login(code, email=self.email)["user"], self.email)

	def test_staff_login_opt_in_does_not_allow_public_desk_role_signup(self):
		self.configure(allow_system_user_login=1, default_user_role="System Manager")
		code = self.code()
		with self.actor("Guest"), self.assertRaises(frappe.PermissionError):
			login(code, email=self.email)
		self.assertFalse(frappe.db.exists("User", self.email))
