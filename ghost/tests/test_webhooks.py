import hashlib
import hmac
import json
from unittest.mock import patch

import frappe

from ghost.events import generate_signature, on_ghost_converted, send_webhook
from ghost.tests.helpers import GhostIntegrationCase

_hook_calls = []


def _recording_hook(**kwargs):
	_hook_calls.append(kwargs)


def _failing_hook(**kwargs):
	raise RuntimeError("test listener failure")


class TestEventWebhooks(GhostIntegrationCase):
	def test_nothing_fires_when_webhooks_disabled(self):
		with patch("frappe.enqueue") as enqueue, patch("frappe.publish_realtime") as publish:
			on_ghost_converted("anonymous", self.email, "rename")
		enqueue.assert_not_called()
		publish.assert_not_called()

	def test_webhook_enqueued_and_realtime_published_when_enabled(self):
		self.configure(
			enable_webhooks=1,
			webhook_url="https://example.invalid/hook",
			webhook_secret="test-secret",
			enable_realtime_events=1,
		)
		with patch("frappe.enqueue") as enqueue, patch("frappe.publish_realtime") as publish:
			on_ghost_converted("anonymous", self.email, "rename", tokens={"access_token": "never-send"})
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(enqueue.call_args.kwargs["secret"], "test-secret")
		self.assertNotIn("access_token", json.dumps(enqueue.call_args.kwargs["payload"]))
		self.assertEqual(publish.call_args.kwargs, {"user": self.email, "after_commit": True})

	def test_hmac_signature_generation(self):
		body = json.dumps({"event": "ghost_converted"})
		self.assertEqual(
			generate_signature(body, "test-secret"),
			hmac.new(b"test-secret", body.encode(), hashlib.sha256).hexdigest(),
		)
		with patch("frappe.integrations.utils.make_post_request") as post:
			send_webhook("https://example.invalid/hook", "test-secret", {"event": "ghost_converted"})
		kwargs = post.call_args.kwargs
		self.assertEqual(
			kwargs["headers"]["X-Ghost-Signature"], generate_signature(kwargs["data"], "test-secret")
		)

	def test_failing_hook_does_not_break_dispatcher(self):
		self.configure(enable_webhooks=1, webhook_url=None, enable_realtime_events=0)
		_hook_calls.clear()
		original_hooks = frappe.get_hooks

		def hooks(name=None, *args, **kwargs):
			if name == "ghost_conversion_hooks":
				return [
					"ghost.tests.test_webhooks._failing_hook",
					"ghost.tests.test_webhooks._recording_hook",
				]
			return original_hooks(name, *args, **kwargs)

		with patch("frappe.get_hooks", side_effect=hooks), patch("frappe.log_error"):
			on_ghost_converted("anonymous", self.email, "rename")
		self.assertEqual(len(_hook_calls), 1)

	def test_conversion_fires_dispatcher(self):
		self.configure(enable_webhooks=1, webhook_url=None)
		source = self.new_ghost()["user"]
		with patch("ghost.events.on_ghost_converted") as dispatch:
			self.convert(source)
		self.assertEqual(dispatch.call_args.args[:3], (source, self.email, "rename"))
