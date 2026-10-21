from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from ghost.api.magic_link import consume_magic_link, send_magic_link
from ghost.tests.helpers import GhostIntegrationCase
from ghost.www.convert import get_context


class TestMagicLink(GhostIntegrationCase):
	def setUp(self):
		super().setUp()
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": self.tag,
				"subject": "Verify email",
				"response": "{{ magic_link }}",
			}
		).insert()
		self.configure(
			enable_magic_link=1, magic_link_expiry_minutes=10, magic_link_email_template=template.name
		)
		self.source = self.new_ghost()["user"]

	def send(self):
		with self.actor(self.source), patch("frappe.sendmail"):
			result = send_magic_link(self.source, self.email)
		name = frappe.db.get_value(
			"Ghost Magic Link Token", {"ghost_email": self.source, "status": "Pending"}, "name"
		)
		return result, frappe.get_doc("Ghost Magic Link Token", name)

	def test_send_magic_link_fails_when_disabled(self):
		self.configure(enable_magic_link=0)
		with self.actor(self.source), self.assertRaises(frappe.ValidationError):
			send_magic_link(self.source, self.email)

	def test_send_magic_link_generates_token_without_returning_it(self):
		result, token = self.send()
		self.assertEqual(set(result), {"status", "message"})
		self.assertTrue(token.token)

	def test_convert_magic_link_success(self):
		_, token = self.send()
		with self.actor(self.source):
			result = consume_magic_link(token.token)
		self.assertEqual(result["user"], self.email)
		self.assertEqual(token.reload().status, "Used")
		with self.actor(self.email), self.assertRaises(frappe.ValidationError):
			consume_magic_link(token.token)

	def test_convert_magic_link_expired(self):
		_, token = self.send()
		token.db_set("expires_on", add_to_date(now_datetime(), minutes=-1))
		frappe.form_dict = frappe._dict(token=token.token)
		context = frappe._dict()
		get_context(context)
		self.assertEqual(context.error_message, "This magic link has expired.")
		with self.actor(self.source), self.assertRaises(frappe.ValidationError):
			consume_magic_link(token.token)

	def test_another_source_cannot_consume_link(self):
		_, token = self.send()
		other = self.new_ghost()["user"]
		with self.actor(other), self.assertRaises(frappe.PermissionError):
			consume_magic_link(token.token)
		self.assertEqual(token.reload().status, "Pending")

	def test_delivery_failure_is_not_success(self):
		with self.actor(self.source), patch("frappe.sendmail", side_effect=RuntimeError("transport down")):
			with self.assertRaises(frappe.ValidationError):
				send_magic_link(self.source, self.email)

	def test_native_html_email_template_is_used(self):
		template = frappe.get_doc("Email Template", self.settings.magic_link_email_template)
		template.use_html = 1
		template.response_html = "<p>Verified link: {{ magic_link }}</p>"
		template.save()
		with self.actor(self.source), patch("frappe.sendmail") as send:
			send_magic_link(self.source, self.email)
		self.assertIn("Verified link:", send.call_args.kwargs["content"])
		self.assertIn("/convert?token=", send.call_args.kwargs["content"])
