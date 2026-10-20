"""Fast negative tests using the real API functions and mocked persistence."""

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

from ghost import security
from ghost.api import auth, ghost, magic_link, social
from ghost.api import otp as otp_api
from ghost.ghost.doctype.otp import otp
from ghost.tests.unit_helpers import local_attribute


class TestAuthenticationBoundaries(unittest.TestCase):
	def setUp(self):
		self.db = Mock()
		self.settings = frappe._dict(
			enable_ghost_feature=1,
			enable_otp_login=1,
			allow_public_signup=1,
			ghost_role="Ghost",
			ghost_email_domain="guest.local",
			client_id="configured",
			sandbox_mode=0,
			max_otp_attempts=5,
			enable_social_login=1,
			enable_magic_link=1,
			google_client_id="google",
			magic_link_email_template="mock",
			magic_link_expiry_minutes=10,
			access_token_expiry_seconds=3600,
			ghost_token_scope="all",
		)

		def raise_error(message, exception=frappe.ValidationError, **kwargs):
			raise exception(message)

		patchers = [
			local_attribute("flags", frappe._dict(in_test=False)),
			patch.object(frappe, "request", None),
			patch.object(frappe, "get_system_settings", return_value="UTC"),
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "throw", side_effect=raise_error),
			patch.object(frappe, "session", SimpleNamespace(user="Guest")),
			patch.object(frappe, "get_single", return_value=self.settings),
			patch.object(frappe, "get_cached_doc", return_value=self.settings),
		]
		patchers += [
			patch.object(m, "_", lambda text: text)
			for m in (security, auth, ghost, magic_link, otp_api, social, otp)
		]
		for p in patchers:
			p.__enter__()
			self.addCleanup(p.__exit__, None, None, None)

	def test_existing_email_is_rejected_before_user_or_token_operations(self):
		with (
			patch.object(frappe, "get_doc") as get_doc,
			patch.object(auth, "generate_oauth_tokens") as tokens,
		):
			with self.assertRaises(frappe.PermissionError):
				ghost.create_ghost_session(email="owner@example.invalid")
		get_doc.assert_not_called()
		tokens.assert_not_called()

	def test_fingerprint_never_resumes_an_existing_user(self):
		self.db.get_value.return_value = 0
		user = Mock(name="new-user")
		user.name = "ghost_new@guest.local"
		with (
			patch.object(frappe, "get_doc", return_value=user),
			patch.object(auth, "generate_oauth_tokens", return_value={}) as tokens,
		):
			result = ghost.create_ghost_session(fingerprint="copied-fingerprint")
		self.assertEqual(result["user"], user.name)
		self.assertTrue(self.db.get_value.call_args.args[0] == "Role")
		tokens.assert_called_once_with(user.name)

	def test_caller_cannot_bypass_otp_or_claim_provider_verification(self):
		for options in ({"bypass_otp": True}, {"conversion_channel": "Google"}):
			with self.subTest(options=options), patch.object(ghost, "_convert_verified_user") as convert:
				with self.assertRaises(frappe.PermissionError):
					ghost.convert_to_real_user(
						"ghost_12345678@guest.local", "owner@example.invalid", **options
					)
				convert.assert_not_called()

	def test_cross_ghost_and_regular_account_sources_are_rejected(self):
		for actor, source in (
			("Guest", "ghost_12345678@guest.local"),
			("ghost_12345678@guest.local", "ghost_87654321@guest.local"),
			("owner@example.invalid", "owner@example.invalid"),
		):
			frappe.session.user = actor
			with self.subTest(actor=actor), self.assertRaises(frappe.PermissionError):
				security.require_owned_ghost(source)

	def test_disabled_or_staff_ghost_is_rejected(self):
		frappe.session.user = "ghost_12345678@guest.local"
		for enabled, user_type in ((0, "Website User"), (1, "System User")):
			self.db.get_value.return_value = frappe._dict(enabled=enabled, user_type=user_type)
			with self.subTest(enabled=enabled), self.assertRaises(frappe.PermissionError):
				security.require_owned_ghost(frappe.session.user)

	def test_google_checks_source_ownership_before_contacting_provider(self):
		with patch.object(social.requests, "get") as get:
			with self.assertRaises(frappe.PermissionError):
				social.convert_with_google("ghost_12345678@guest.local", "not-a-real-token")
		get.assert_not_called()

	def test_magic_link_requires_source_session(self):
		with self.assertRaises(frappe.PermissionError):
			magic_link.send_magic_link("ghost_12345678@guest.local", "owner@example.invalid")
		self.db.get_value.assert_not_called()

	def test_magic_link_response_never_contains_login_secret(self):
		self.db.get_value.return_value = None
		template = frappe._dict(subject="test", response="test")
		with (
			patch.object(security, "require_owned_ghost", return_value="ghost_12345678@guest.local"),
			patch.object(frappe, "get_doc", side_effect=[Mock(), template]),
			patch.object(frappe, "render_template", return_value="test"),
			patch.object(frappe, "sendmail"),
			patch.object(frappe.utils, "get_url", return_value="https://example.invalid"),
		):
			result = magic_link.send_magic_link("ghost_12345678@guest.local", "owner@example.invalid")
		self.assertEqual(set(result), {"status", "message"})
		self.assertNotIn("token=", json.dumps(result))

	def test_mixed_login_identifiers_are_rejected_before_otp(self):
		with patch.object(auth, "ghost_verify_otp") as verify:
			with self.assertRaises(frappe.ValidationError):
				auth.login("123456", email="victim@example.invalid", mobile_no="+919876543210")
		verify.assert_not_called()

	def test_cookie_login_does_not_issue_bearer_tokens_by_default(self):
		self.db.get_value.return_value = "owner@example.invalid"
		with (
			patch.object(auth, "ghost_verify_otp") as verify,
			patch.object(auth, "require_enabled_user"),
			patch.object(auth, "generate_oauth_tokens") as tokens,
			local_attribute("request", None),
		):
			result = auth.login("123456", email="Owner@Example.Invalid")
		verify.assert_called_once_with(
			otp_code="123456", email="owner@example.invalid", phone=None, purpose="Login"
		)
		tokens.assert_not_called()
		self.assertEqual(result["user"], "owner@example.invalid")

	def test_builtin_or_disabled_accounts_cannot_get_tokens(self):
		self.db.get_value.return_value = 0
		for user in ("Guest", "Administrator", "disabled@example.invalid"):
			with self.subTest(user=user), self.assertRaises(frappe.AuthenticationError):
				auth.generate_oauth_tokens(user)

	def test_staff_login_requires_explicit_policy(self):
		self.db.get_value.side_effect = [1, "System User"]
		with self.assertRaises(frappe.PermissionError):
			security.require_enabled_user("staff@example.invalid")

	def test_verification_without_recipient_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			otp.verify("123456")
		self.db.get_value.assert_not_called()

	def test_otp_consumption_is_locked_and_has_no_internal_commit(self):
		self.db.get_value.return_value = frappe._dict(
			name="OTP-mock",
			otp_code="123456",
			expiry="2099-01-01 00:00:00",
			status="Valid",
			email="owner@example.invalid",
			phone=None,
			purpose="Login",
		)
		with patch.object(otp, "limit_verification"):
			self.assertTrue(otp.verify("123456", email="owner@example.invalid")["valid"])
		self.assertTrue(self.db.get_value.call_args.kwargs["for_update"])
		self.db.set_value.assert_called_once_with("OTP", "OTP-mock", "status", "Expired")
		self.db.commit.assert_not_called()

	def test_wrong_otp_does_not_consume_or_authenticate(self):
		self.db.get_value.return_value = frappe._dict(
			name="OTP-mock",
			otp_code="123456",
			expiry="2099-01-01 00:00:00",
			status="Valid",
			email="owner@example.invalid",
			phone=None,
			purpose="Login",
		)
		with patch.object(otp, "limit_verification"), self.assertRaises(frappe.ValidationError):
			otp.verify("wrong", email="owner@example.invalid")
		self.db.set_value.assert_not_called()

	def test_failed_guess_limit_is_enforced_outside_transaction(self):
		cache = Mock()
		cache.eval.return_value = 6
		with patch.object(frappe, "cache", return_value=cache):
			with self.assertRaises(frappe.RateLimitExceededError):
				security.limit_verification("owner@example.invalid", "Login", 5)
		self.db.commit.assert_not_called()

	def test_fixed_otp_sandbox_cannot_run_outside_tests(self):
		with patch.object(frappe, "flags", frappe._dict(in_test=False)):
			with self.assertRaises(frappe.PermissionError):
				security.require_test_sandbox(frappe._dict(sandbox_mode=1))

	def test_public_otp_response_excludes_codes_and_transport_details(self):
		with patch.object(
			otp_api,
			"generate_otp",
			return_value={"sent": True, "otp_code": "secret", "name": "private", "send_results": ["private"]},
		):
			result = otp_api.send_otp(email="owner@example.invalid")
		self.assertEqual(set(result), {"status", "message"})

	def test_failed_delivery_is_not_reported_as_success(self):
		with patch.object(otp_api, "generate_otp", return_value={"sent": False}):
			with self.assertRaises(frappe.ValidationError):
				otp_api.send_otp(email="owner@example.invalid")

	def test_private_converter_is_not_an_http_api(self):
		self.assertNotIn(ghost._convert_verified_user, frappe.whitelisted)
		for method in (
			auth.login,
			auth.refresh_bearer_token,
			ghost.create_ghost_session,
			ghost.convert_to_real_user,
			social.convert_with_google,
			magic_link.send_magic_link,
			magic_link.consume_magic_link,
		):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["POST"])

	def test_otp_metadata_grants_no_guest_access(self):
		root = Path(__file__).resolve().parents[1]
		meta = json.loads((root / "ghost/doctype/otp/otp.json").read_text())
		self.assertNotIn("Guest", [p["role"] for p in meta["permissions"]])
		self.assertFalse(meta["index_web_pages_for_search"])

	def test_otp_login_is_disabled_until_explicitly_enabled(self):
		self.settings.enable_otp_login = 0
		with patch.object(auth, "ghost_verify_otp") as verify:
			with self.assertRaises(frappe.PermissionError):
				auth.login("123456", email="owner@example.invalid")
		verify.assert_not_called()

	def test_signup_requires_explicit_permission(self):
		self.settings.allow_public_signup = 0
		with patch.object(frappe, "get_doc") as get:
			with self.assertRaises(frappe.PermissionError):
				auth.create_new_user("new@example.invalid")
		get.assert_not_called()

	def test_conversion_notifications_are_private_and_wait_for_commit(self):
		from ghost.events import on_ghost_converted

		settings = Mock(
			enable_webhooks=1, webhook_url="https://example.invalid/hook", enable_realtime_events=1
		)
		settings.get_password.return_value = "mock-secret"
		with (
			patch.object(frappe, "get_single", return_value=settings),
			patch.object(frappe, "get_hooks", return_value=[]),
			patch.object(frappe, "enqueue") as enqueue,
			patch.object(frappe, "publish_realtime") as publish,
		):
			on_ghost_converted(
				"ghost_12345678@guest.local",
				"owner@example.invalid",
				"rename",
				tokens={"access_token": "private"},
			)
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(publish.call_args.kwargs, {"user": "owner@example.invalid", "after_commit": True})
		self.assertNotIn("access_token", json.dumps(enqueue.call_args.kwargs["payload"]))

	def test_revoked_token_cannot_be_rotated_after_lock(self):
		self.db.get_value.side_effect = ["token-name", frappe._dict(status="Revoked", refresh_token="old")]
		with patch.object(auth, "generate_oauth_tokens") as generate:
			with self.assertRaises(frappe.AuthenticationError):
				auth.refresh_bearer_token("old")
		generate.assert_not_called()
		self.assertEqual(self.db.get_value.call_args.args[1], "token-name")
		self.assertTrue(self.db.get_value.call_args.kwargs["for_update"])

	def test_cookie_login_rejects_untrusted_browser_origin(self):
		request = SimpleNamespace(
			headers={"Origin": "https://attacker.invalid"}, scheme="https", host="portal.invalid"
		)
		with (
			local_attribute("request", request),
			patch.object(frappe, "conf", frappe._dict(allow_cors=["*"])),
		):
			with self.assertRaises(frappe.PermissionError):
				security.require_trusted_login_origin()

	def test_cookie_login_accepts_explicit_headless_origin(self):
		request = SimpleNamespace(
			headers={"Origin": "https://portal.invalid"}, scheme="https", host="backend.invalid"
		)
		with (
			local_attribute("request", request),
			patch.object(frappe, "conf", frappe._dict(allow_cors=["https://portal.invalid"])),
		):
			security.require_trusted_login_origin()
