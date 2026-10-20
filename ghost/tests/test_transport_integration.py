import email
import email.policy
import re
from unittest.mock import patch

import frappe

from ghost.api.auth import login
from ghost.api.magic_link import consume_magic_link, send_magic_link
from ghost.api.otp import send_otp
from ghost.events import generate_signature, send_webhook
from ghost.tests.helpers import GhostIntegrationCase
from ghost.tests.local_services import smtp_capture, webhook_capture


class TestRealTransports(GhostIntegrationCase):
	def prepare_mail(self, port):
		account = frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": f"Ghost SMTP {self.tag[:8]}",
				"email_id": "sender-" + self.email,
				"enable_outgoing": 1,
				"enable_incoming": 0,
				"smtp_server": "127.0.0.1",
				"smtp_port": str(port),
				"use_tls": 0,
				"use_ssl_for_outgoing": 0,
				"no_smtp_authentication": 1,
			}
		).insert()
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Ghost mail {self.tag}",
				"subject": "Ghost verification",
				"response": "Code {{ otp_code }}",
			}
		).insert()
		self.configure(email_account=account.name, email_template=template.name)

	def deliver_queued_messages(self):
		# Frappe's queue owns its own commits. Suppress only those commits so test
		# records stay rollback-owned; SQL updates and the SMTP transport are real.
		names = frappe.get_all(
			"Email Queue",
			filters={"sender": ["like", "%" + self.email + "%"], "status": "Not Sent"},
			pluck="name",
		)
		with (
			patch.dict(frappe.flags, {"testing_email": True, "mute_emails": False}),
			patch.object(frappe.db, "commit"),
		):
			for name in names:
				frappe.get_doc("Email Queue", name).send()
		return len(names)

	def body(self, raw):
		message = email.message_from_bytes(raw, policy=email.policy.default)
		return "\n".join(
			part.get_content()
			for part in message.walk()
			if part.get_content_type() in ("text/plain", "text/html")
		)

	def test_real_smtp_delivers_code_used_for_login(self):
		with smtp_capture() as server:
			self.prepare_mail(server.server_address[1])
			with (
				patch.dict(frappe.flags, {"testing_email": True, "mute_emails": False}),
				patch.object(frappe.db, "commit"),
			):
				result = send_otp(email=self.email, purpose="Login")
			self.assertEqual(result["status"], "success")
			# v15 can send now; v16 can defer until commit. Flush only pending mail.
			self.deliver_queued_messages()
			self.assertEqual(len(server.messages), 1)
			code = re.search(r"Code (\d{6})", self.body(server.messages[0])).group(1)
			self.assertNotIn(code, str(result))
			with self.actor("Guest"):
				self.assertEqual(login(code, email=self.email)["user"], self.email)

	def test_real_smtp_magic_link_requires_source_and_target_proofs(self):
		with smtp_capture() as server:
			self.prepare_mail(server.server_address[1])
			template = frappe.get_doc(
				{
					"doctype": "Email Template",
					"name": "link-" + self.tag,
					"subject": "Verify",
					"response": "Open {{ magic_link }}",
				}
			).insert()
			self.configure(enable_magic_link=1, magic_link_email_template=template.name)
			source = self.new_ghost()["user"]
			with (
				self.actor(source),
				patch.dict(frappe.flags, {"testing_email": True, "mute_emails": False}),
				patch.object(frappe.db, "commit"),
			):
				result = send_magic_link(source, self.email)
			# v15 can send now; v16 can defer until commit. Flush only pending mail.
			self.deliver_queued_messages()
			self.assertEqual(len(server.messages), 1)
			token = re.search(r"/convert\?token=([A-Za-z0-9_-]+)", self.body(server.messages[0])).group(1)
			self.assertNotIn(token, str(result))
			with self.actor("Guest"), self.assertRaises(frappe.PermissionError):
				consume_magic_link(token)
			with self.actor(source):
				self.assertEqual(consume_magic_link(token)["user"], self.email)

	def test_real_http_webhook_signature_covers_exact_wire_body(self):
		with webhook_capture() as server:
			payload = {"event": "ghost_converted", "real_email": self.email}
			send_webhook(f"http://127.0.0.1:{server.server_address[1]}/events", "test-secret", payload)
			self.assertEqual(len(server.messages), 1)
			body, signature = server.messages[0]
			self.assertEqual(signature, generate_signature(body.decode(), "test-secret"))
			self.assertNotIn(b"access_token", body)
