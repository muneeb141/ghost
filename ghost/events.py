import hashlib
import hmac
import json

import frappe
from frappe.utils import now_datetime


def generate_signature(payload_body, secret):
	"""Return the HMAC-SHA256 hex digest of the raw webhook payload body."""
	return hmac.new(
		secret.encode("utf-8"), payload_body.encode("utf-8"), hashlib.sha256
	).hexdigest()


def on_ghost_converted(ghost_email, real_email, conversion_mode, tokens=None):
	"""Fire all registered events when a ghost user converts.

	Failure-safe by design: every error is logged and swallowed so a broken
	integration can never break the conversion flow. `tokens` is accepted for
	caller convenience but is NEVER included in any outgoing payload.
	"""
	try:
		settings = frappe.get_single("Ghost Settings")
		if not settings.enable_webhooks:
			return

		payload = {
			"event": "ghost_converted",
			"ghost_email": ghost_email,
			"real_email": real_email,
			"conversion_mode": conversion_mode,
			"timestamp": str(now_datetime()),
		}

		# 1. Enqueue the signed webhook so a slow endpoint never blocks conversion.
		if settings.webhook_url:
			frappe.enqueue(
				"ghost.events.send_webhook",
				queue="short",
				url=settings.webhook_url,
				secret=settings.get_password("webhook_secret"),
				payload=payload,
			)

		# 2. Publish a Frappe realtime event for connected clients.
		if settings.enable_realtime_events:
			frappe.publish_realtime("ghost_converted", payload)

		# 3. Fire Frappe hooks registered by other apps. One bad listener must
		# not break the remaining listeners or the conversion.
		for handler in frappe.get_hooks("ghost_conversion_hooks"):
			try:
				frappe.call(
					handler,
					ghost_email=ghost_email,
					real_email=real_email,
					conversion_mode=conversion_mode,
				)
			except Exception as e:
				frappe.log_error(f"Ghost conversion hook {handler} failed: {str(e)}")
	except Exception as e:
		frappe.log_error(f"Ghost conversion event dispatch failed: {str(e)}")


def send_webhook(url, secret, payload):
	"""POST the conversion payload with an HMAC-SHA256 signature header.

	Runs as a background job (enqueued by on_ghost_converted). The receiver
	verifies authenticity by recomputing HMAC-SHA256 over the raw request body
	with the shared secret and comparing it to the X-Ghost-Signature header.
	"""
	from frappe.integrations.utils import make_post_request

	body = json.dumps(payload)
	headers = {"Content-Type": "application/json"}
	if secret:
		headers["X-Ghost-Signature"] = generate_signature(body, secret)

	try:
		make_post_request(url, data=body, headers=headers)
	except Exception as e:
		frappe.log_error(f"Ghost webhook delivery to {url} failed: {str(e)}")
