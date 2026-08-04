import hashlib
import hmac
import json
import unittest
from unittest import mock

import frappe

from ghost.api.ghost import convert_to_real_user, create_ghost_session
from ghost.events import generate_signature, on_ghost_converted, send_webhook


_hook_calls = []


def _recording_hook(ghost_email=None, real_email=None, conversion_mode=None):
	_hook_calls.append({
		"ghost_email": ghost_email,
		"real_email": real_email,
		"conversion_mode": conversion_mode,
	})


def _failing_hook(ghost_email=None, real_email=None, conversion_mode=None):
	raise Exception("Listener exploded")


class TestEventWebhooks(unittest.TestCase):
	def setUp(self):
		# Ensure Ghost Role exists
		if not frappe.db.exists("Role", "Ghost"):
			frappe.get_doc({"doctype": "Role", "role_name": "Ghost"}).insert(ignore_permissions=True)

		settings = frappe.get_single("Ghost Settings")
		settings.enable_ghost_feature = 1
		settings.ghost_role = "Ghost"
		settings.verify_otp_on_conversion = 0
		settings.default_user_role = None
		settings.enable_webhooks = 0
		settings.webhook_url = None
		settings.webhook_secret = None
		settings.enable_realtime_events = 0
		settings.save()

		# Token generation requires a valid OAuth Client; the site's configured
		# client may not exist in test databases, so ensure one does.
		# Note: generate_oauth_tokens looks up OAuth Client by document name.
		client_id = settings.client_id
		if not client_id or not frappe.db.exists("OAuth Client", client_id):
			c = frappe.new_doc("OAuth Client")
			c.app_name = "Ghost Webhooks Test"
			c.skat = "1"  # Skip Authorization
			c.default_redirect_uri = "http://localhost"
			c.redirect_uris = "http://localhost"
			c.save(ignore_permissions=True)
			client_id = c.name
		settings.client_id = client_id
		settings.save()

		_hook_calls.clear()

	def tearDown(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_webhooks = 0
		settings.webhook_url = None
		settings.webhook_secret = None
		settings.enable_realtime_events = 0
		settings.save()
		frappe.db.commit() # nosemgrep: frappe-manual-commit - required in test tearDown to reset webhook settings across test cases

	def test_nothing_fires_when_webhooks_disabled(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_webhooks = 0
		settings.webhook_url = "https://example.com/hook"
		settings.enable_realtime_events = 1
		settings.save()

		with mock.patch("frappe.enqueue") as mock_enqueue, \
			mock.patch("frappe.publish_realtime") as mock_publish:
			on_ghost_converted("ghost_x@guest.local", "real@example.com", "rename")

		mock_enqueue.assert_not_called()
		mock_publish.assert_not_called()
		self.assertEqual(_hook_calls, [])
		print("\n[Success] No webhook, realtime event, or hook fired with webhooks disabled")

	def test_webhook_enqueued_and_realtime_published_when_enabled(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_webhooks = 1
		settings.webhook_url = "https://example.com/hook"
		settings.webhook_secret = "topsecret"
		settings.enable_realtime_events = 1
		settings.save()

		with mock.patch("frappe.enqueue") as mock_enqueue, \
			mock.patch("frappe.publish_realtime") as mock_publish:
			on_ghost_converted(
				"ghost_x@guest.local", "real@example.com", "rename",
				tokens={"access_token": "should-never-leak"},
			)

		mock_enqueue.assert_called_once()
		enqueue_kwargs = mock_enqueue.call_args.kwargs
		self.assertEqual(enqueue_kwargs["queue"], "short")
		self.assertEqual(enqueue_kwargs["url"], "https://example.com/hook")
		# Password field must be decrypted for signing, not the asterisk placeholder
		self.assertEqual(enqueue_kwargs["secret"], "topsecret")

		payload = enqueue_kwargs["payload"]
		self.assertEqual(payload["event"], "ghost_converted")
		self.assertEqual(payload["ghost_email"], "ghost_x@guest.local")
		self.assertEqual(payload["real_email"], "real@example.com")
		self.assertEqual(payload["conversion_mode"], "rename")
		self.assertIn("timestamp", payload)
		# Tokens must never be included in outgoing payloads
		self.assertNotIn("access_token", json.dumps(payload))

		mock_publish.assert_called_once()
		publish_args = mock_publish.call_args.args
		self.assertEqual(publish_args[0], "ghost_converted")
		self.assertNotIn("access_token", json.dumps(publish_args[1]))
		print("\n[Success] Webhook enqueued and realtime event published with webhooks enabled")

	def test_hmac_signature_generation(self):
		body = json.dumps({"event": "ghost_converted", "real_email": "real@example.com"})
		expected = hmac.new(b"topsecret", body.encode("utf-8"), hashlib.sha256).hexdigest()
		self.assertEqual(generate_signature(body, "topsecret"), expected)

		# End-to-end: send_webhook must attach the correct signature header
		payload = {"event": "ghost_converted", "real_email": "real@example.com"}
		with mock.patch("frappe.integrations.utils.make_post_request") as mock_post:
			send_webhook("https://example.com/hook", "topsecret", payload)

		mock_post.assert_called_once()
		post_kwargs = mock_post.call_args.kwargs
		expected_header = hmac.new(
			b"topsecret", post_kwargs["data"].encode("utf-8"), hashlib.sha256
		).hexdigest()
		self.assertEqual(post_kwargs["headers"]["X-Ghost-Signature"], expected_header)
		print("\n[Success] HMAC-SHA256 signature matches expected digest")

	def test_failing_hook_does_not_break_dispatcher(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_webhooks = 1
		settings.save()

		hooks = [
			"ghost.tests.test_webhooks._failing_hook",
			"ghost.tests.test_webhooks._recording_hook",
		]
		with mock.patch("frappe.get_hooks", return_value=hooks), \
			mock.patch("frappe.log_error"):
			# Must not raise despite the first listener exploding
			on_ghost_converted("ghost_x@guest.local", "real@example.com", "manual_migration")

		self.assertEqual(len(_hook_calls), 1)
		self.assertEqual(_hook_calls[0]["ghost_email"], "ghost_x@guest.local")
		self.assertEqual(_hook_calls[0]["real_email"], "real@example.com")
		self.assertEqual(_hook_calls[0]["conversion_mode"], "manual_migration")
		print("\n[Success] Failing hook was logged and remaining hooks still ran")

	def test_conversion_fires_dispatcher(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_webhooks = 1
		settings.save()

		real_email = "webhooks_e2e@example.com"
		if frappe.db.exists("User", real_email):
			frappe.delete_doc("User", real_email, force=True)

		ghost_email = create_ghost_session()["user"]
		with mock.patch("ghost.events.on_ghost_converted") as mock_dispatch:
			result = convert_to_real_user(ghost_email, real_email)

		self.assertEqual(result.get("conversion_mode"), "rename")
		mock_dispatch.assert_called_once()
		dispatch_args = mock_dispatch.call_args.args
		self.assertEqual(dispatch_args[0], ghost_email)
		self.assertEqual(dispatch_args[1], real_email)
		self.assertEqual(dispatch_args[2], "rename")

		frappe.delete_doc("User", real_email, force=True)
		print(f"\n[Success] Conversion {ghost_email} -> {real_email} fired the event dispatcher")
