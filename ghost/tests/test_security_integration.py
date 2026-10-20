"""Real database/Redis regression tests. Run only on a disposable site."""

import uuid
from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

try:
	from frappe.tests import IntegrationTestCase
except ImportError:
	from frappe.tests.utils import FrappeTestCase as IntegrationTestCase

from ghost.api import auth, ghost, magic_link, social
from ghost.ghost.doctype.otp.otp import generate, verify


class TestSecurityIntegration(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.suffix = uuid.uuid4().hex
		frappe.local.request_ip = "security-test-" + self.suffix
		self.email = f"ghost-security-{self.suffix}@example.invalid"
		if not frappe.db.exists("Role", "Ghost"):
			frappe.get_doc({"doctype": "Role", "role_name": "Ghost", "desk_access": 0}).insert()
		client = frappe.get_doc(
			{
				"doctype": "OAuth Client",
				"app_name": f"Ghost security {self.suffix}",
				"default_redirect_uri": "https://example.invalid/callback",
				"redirect_uris": "https://example.invalid/callback",
				"scopes": "all",
			}
		).insert()
		settings = frappe.get_single("Ghost Settings")
		settings.update(
			{
				"enable_ghost_feature": 1,
				"enable_otp_login": 1,
				"allow_public_signup": 1,
				"ghost_role": "Ghost",
				"ghost_email_domain": "guest.local",
				"client_id": client.name,
				"sandbox_mode": 0,
				"default_user_role": None,
				"enable_webhooks": 0,
				"enable_lead_capture": 0,
				"enable_multi_device_merge": 0,
				"allow_system_user_login": 0,
				"max_otp_attempts": 5,
				"otp_delivery_type": "Email",
				"otp_length": 6,
				"otp_code_type": "Numeric",
				"expiry_time_minutes": 10,
			}
		)
		settings.save()
		frappe.clear_document_cache("Ghost Settings", "Ghost Settings")
		self.settings = settings
		self.addCleanup(frappe.set_user, "Administrator")

	def create_account(self, email=None):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email or self.email,
				"first_name": "Security Test",
				"enabled": 1,
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		return user

	def test_existing_account_email_cannot_be_used_for_guest_session(self):
		user = self.create_account()
		frappe.set_user("Guest")
		before = frappe.db.count("OAuth Bearer Token", {"user": user.name})
		with self.assertRaises(frappe.PermissionError):
			ghost.create_ghost_session(email=user.name)
		self.assertEqual(before, frappe.db.count("OAuth Bearer Token", {"user": user.name}))

	def test_duplicate_fingerprint_cannot_reconnect(self):
		self.settings.enable_fingerprinting = 1
		self.settings.save()
		frappe.set_user("Guest")
		a = ghost.create_ghost_session(fingerprint=self.suffix)
		b = ghost.create_ghost_session(fingerprint=self.suffix)
		self.assertNotEqual(a["user"], b["user"])

	def test_cross_ghost_conversion_and_bypass_are_denied(self):
		a = ghost.create_ghost_session()
		b = ghost.create_ghost_session()
		frappe.set_user(a["user"])
		for source, options in ((b["user"], {}), (a["user"], {"bypass_otp": True})):
			with self.assertRaises(frappe.PermissionError):
				ghost.convert_to_real_user(source, self.email, **options)
		self.assertFalse(frappe.db.exists("User", self.email))

	def test_otp_is_recipient_purpose_bound_and_single_use(self):
		code = generate(email=self.email, purpose="Login", send=False)["otp_code"]
		for recipient, purpose in (("other-" + self.email, "Login"), (self.email, "Conversion")):
			with self.assertRaises(frappe.ValidationError):
				verify(code, email=recipient, purpose=purpose)
		self.assertTrue(verify(code, email=self.email, purpose="Login")["valid"])
		with self.assertRaises(frappe.ValidationError):
			verify(code, email=self.email, purpose="Login")

	def test_expired_otp_is_rejected(self):
		result = generate(email=self.email, send=False)
		frappe.db.set_value("OTP", result["name"], "expiry", add_to_date(now_datetime(), minutes=-1))
		with self.assertRaises(frappe.ValidationError):
			verify(result["otp_code"], email=self.email)

	def test_guess_counter_survives_savepoint_rollback(self):
		generate(email=self.email, send=False)
		for _ in range(5):
			frappe.db.savepoint("wrong_guess")
			with self.assertRaises(frappe.ValidationError):
				verify("incorrect", email=self.email)
			frappe.db.rollback(save_point="wrong_guess")
		with self.assertRaises(frappe.RateLimitExceededError):
			verify("incorrect", email=self.email)

	def test_guest_has_no_otp_read_or_create_permission(self):
		frappe.set_user("Guest")
		for operation in ("read", "create", "write"):
			self.assertFalse(frappe.has_permission("OTP", operation, user="Guest"))

	def test_email_otp_logs_into_existing_account_without_tokens(self):
		user = self.create_account()
		code = generate(email=user.name, purpose="Login", send=False)["otp_code"]
		frappe.set_user("Guest")
		result = auth.login(code, email=user.name)
		self.assertEqual(result["user"], user.name)
		self.assertNotIn("access_token", result)

	def test_email_otp_signup_creates_website_user(self):
		code = generate(email=self.email, purpose="Login", send=False)["otp_code"]
		frappe.set_user("Guest")
		result = auth.login(code, email=self.email)
		self.assertEqual(result["user"], self.email)
		self.assertEqual(frappe.db.get_value("User", self.email, "user_type"), "Website User")

	def test_valid_conversion_revokes_old_tokens_and_uses_native_rename(self):
		data = ghost.create_ghost_session()
		code = generate(email=self.email, purpose="Conversion", send=False)["otp_code"]
		frappe.set_user(data["user"])
		result = ghost.convert_to_real_user(data["user"], self.email, otp_code=code)
		self.assertEqual(result["user"], self.email)
		self.assertFalse(frappe.db.exists("User", data["user"]))
		self.assertEqual(
			frappe.db.get_value("OAuth Bearer Token", {"access_token": data["access_token"]}, "status"),
			"Revoked",
		)

	def test_conversion_into_existing_account_preserves_roles(self):
		target = self.create_account()
		roles = frappe.get_roles(target.name)
		data = ghost.create_ghost_session()
		code = generate(email=self.email, purpose="Conversion", send=False)["otp_code"]
		frappe.set_user(data["user"])
		result = ghost.convert_to_real_user(data["user"], self.email, otp_code=code)
		self.assertEqual(result["conversion_mode"], "manual_migration")
		self.assertEqual(frappe.get_roles(target.name), roles)
		self.assertEqual(frappe.db.get_value("User", data["user"], "enabled"), 0)

	def test_refresh_rotates_once_and_old_refresh_is_rejected(self):
		user = self.create_account()
		tokens = auth.generate_oauth_tokens(user.name)
		new = auth.refresh_bearer_token(tokens["refresh_token"])
		self.assertNotEqual(new["refresh_token"], tokens["refresh_token"])
		with self.assertRaises(frappe.AuthenticationError):
			auth.refresh_bearer_token(tokens["refresh_token"])

	def test_disabled_account_cannot_refresh(self):
		user = self.create_account()
		tokens = auth.generate_oauth_tokens(user.name)
		frappe.db.set_value("User", user.name, "enabled", 0)
		with self.assertRaises(frappe.AuthenticationError):
			auth.refresh_bearer_token(tokens["refresh_token"])

	def test_google_cannot_claim_another_ghost(self):
		data = ghost.create_ghost_session()
		frappe.set_user("Guest")
		with patch.object(social.requests, "get") as get:
			with self.assertRaises(frappe.PermissionError):
				social.convert_with_google(data["user"], "not-a-real-token")
		get.assert_not_called()

	def test_conversion_failure_can_be_rolled_back(self):
		data = ghost.create_ghost_session()
		code = generate(email=self.email, purpose="Conversion", send=False)["otp_code"]
		frappe.set_user(data["user"])
		frappe.db.savepoint("conversion_failure")
		with patch.object(
			auth, "generate_oauth_tokens", side_effect=RuntimeError("simulated issuer failure")
		):
			with self.assertRaises(RuntimeError):
				ghost.convert_to_real_user(data["user"], self.email, otp_code=code)
		frappe.db.rollback(save_point="conversion_failure")
		self.assertTrue(frappe.db.exists("User", data["user"]))
		self.assertFalse(frappe.db.exists("User", self.email))
		self.assertEqual(
			frappe.db.get_value("OAuth Bearer Token", {"access_token": data["access_token"]}, "status"),
			"Active",
		)


class TestParallelConsumption(IntegrationTestCase):
	"""Commit only an isolated fixture, then exercise separate real DB connections."""

	def test_parallel_otp_consumes_exactly_once(self):
		from concurrent.futures import ThreadPoolExecutor
		from pathlib import Path
		from threading import Barrier

		frappe.set_user("Administrator")
		email = f"ghost-parallel-{uuid.uuid4().hex}@example.invalid"
		original = frappe.get_single("Ghost Settings").as_dict()
		settings = frappe.get_single("Ghost Settings")
		settings.sandbox_mode = 0
		settings.otp_delivery_type = "Email"
		settings.max_otp_attempts = 5
		settings.save()
		result = generate(email=email, purpose="Login", send=False)
		frappe.db.commit()
		site = frappe.local.site
		sites_path = str(Path(frappe.local.sites_path).resolve())
		barrier = Barrier(2)

		def attempt():
			frappe.init(site=site, sites_path=sites_path, force=True)
			frappe.connect()
			frappe.flags.in_test = True
			frappe.local.request_ip = email
			try:
				barrier.wait(timeout=10)
				verify(result["otp_code"], email=email, purpose="Login")
				frappe.db.commit()
				return "accepted"
			except frappe.ValidationError:
				frappe.db.rollback()
				return "rejected"
			finally:
				frappe.destroy()

		try:
			with ThreadPoolExecutor(max_workers=2) as executor:
				outcomes = list(executor.map(lambda _: attempt(), range(2)))
			self.assertEqual(sorted(outcomes), ["accepted", "rejected"])
		finally:
			frappe.db.delete("OTP", {"name": result["name"]})
			frappe.get_single("Ghost Settings").update(
				{
					k: original.get(k)
					for k in (
						"sandbox_mode",
						"otp_delivery_type",
						"max_otp_attempts",
						"verify_otp_on_conversion",
						"invalidate_ghost_tokens_on_conversion",
					)
				}
			).save()
			frappe.db.commit()

	def test_parallel_refresh_rotates_exactly_once(self):
		from concurrent.futures import ThreadPoolExecutor
		from pathlib import Path
		from threading import Barrier

		frappe.set_user("Administrator")
		original = frappe.get_single("Ghost Settings").client_id
		email = f"ghost-parallel-{uuid.uuid4().hex}@example.invalid"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Parallel test",
				"enabled": 1,
				"send_welcome_email": 0,
			}
		).insert()
		client = frappe.get_doc(
			{
				"doctype": "OAuth Client",
				"app_name": email,
				"default_redirect_uri": "https://example.invalid/callback",
				"redirect_uris": "https://example.invalid/callback",
				"scopes": "all",
			}
		).insert()
		frappe.db.set_single_value("Ghost Settings", "client_id", client.name)
		tokens = auth.generate_oauth_tokens(user.name)
		frappe.db.commit()
		site = frappe.local.site
		sites_path = str(Path(frappe.local.sites_path).resolve())
		barrier = Barrier(2)

		def attempt():
			frappe.init(site=site, sites_path=sites_path, force=True)
			frappe.connect()
			frappe.flags.in_test = True
			try:
				barrier.wait(timeout=10)
				auth.refresh_bearer_token(tokens["refresh_token"])
				frappe.db.commit()
				return "accepted"
			except frappe.AuthenticationError:
				frappe.db.rollback()
				return "rejected"
			finally:
				frappe.destroy()

		try:
			with ThreadPoolExecutor(max_workers=2) as executor:
				outcomes = list(executor.map(lambda _: attempt(), range(2)))
			self.assertEqual(sorted(outcomes), ["accepted", "rejected"])
			self.assertEqual(
				frappe.db.count("OAuth Bearer Token", {"user": user.name, "status": "Active"}), 1
			)
		finally:
			frappe.db.delete("OAuth Bearer Token", {"user": user.name})
			frappe.db.set_single_value("Ghost Settings", "client_id", original)
			frappe.delete_doc("User", user.name, force=True, ignore_permissions=True)
			frappe.delete_doc("OAuth Client", client.name, force=True, ignore_permissions=True)
			frappe.db.commit()
