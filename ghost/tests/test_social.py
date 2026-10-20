from unittest.mock import Mock, patch

import frappe

from ghost.api.social import convert_with_google
from ghost.tests.helpers import GhostIntegrationCase


class TestSocialLogin(GhostIntegrationCase):
	def setUp(self):
		super().setUp()
		self.configure(enable_social_login=1, google_client_id="test-client")
		self.source = self.new_ghost()["user"]

	def response(self, **claims):
		return Mock(
			status_code=200,
			json=lambda: {
				"aud": "test-client",
				"email_verified": True,
				"email": self.email,
				"given_name": "Verified",
				"family_name": "Person",
				**claims,
			},
		)

	def test_convert_with_google_fails_when_disabled(self):
		self.configure(enable_social_login=0)
		with self.actor(self.source), self.assertRaises(frappe.PermissionError):
			convert_with_google(self.source, "not-used")

	def test_convert_with_google_success(self):
		with self.actor(self.source), patch("ghost.api.social.requests.get", return_value=self.response()):
			result = convert_with_google(self.source, "mock-provider-token")
		self.assertEqual(result["user"], self.email)
		self.assertEqual(frappe.db.get_value("User", self.email, "first_name"), "Verified")
		self.assertFalse(frappe.db.exists("User", self.source))

	def test_convert_with_google_invalid_audience(self):
		with (
			self.actor(self.source),
			patch("ghost.api.social.requests.get", return_value=self.response(aud="wrong")),
		):
			with self.assertRaises(frappe.AuthenticationError):
				convert_with_google(self.source, "mock-provider-token")
		self.assertFalse(frappe.db.exists("User", self.email))

	def test_convert_with_google_unverified_email(self):
		with (
			self.actor(self.source),
			patch("ghost.api.social.requests.get", return_value=self.response(email_verified=False)),
		):
			with self.assertRaises(frappe.AuthenticationError):
				convert_with_google(self.source, "mock-provider-token")

	def test_guest_cannot_claim_source_with_valid_target_token(self):
		with self.actor("Guest"), patch("ghost.api.social.requests.get") as provider:
			with self.assertRaises(frappe.PermissionError):
				convert_with_google(self.source, "mock-provider-token")
		provider.assert_not_called()
