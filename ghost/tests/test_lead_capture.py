from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from ghost.api.lead import capture_email
from ghost.tasks import send_lead_reminders
from ghost.tests.helpers import GhostIntegrationCase


class TestLeadCapture(GhostIntegrationCase):
	def setUp(self):
		super().setUp()
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": self.tag,
				"subject": "Continue",
				"response": "{{ captured_email }}",
			}
		).insert()
		self.configure(
			enable_lead_capture=1, lead_reminder_hours=24, lead_reminder_email_template=template.name
		)
		self.source = self.new_ghost()["user"]

	def capture(self, email=None):
		with self.actor(self.source):
			return capture_email(email or self.email)

	def test_capture_email(self):
		self.assertEqual(self.capture()["status"], "success")
		name = frappe.db.get_value("Ghost Lead", {"ghost_email": self.source}, "name")
		self.capture("changed-" + self.email)
		self.assertEqual(frappe.db.get_value("Ghost Lead", name, "captured_email"), "changed-" + self.email)

	def test_capture_email_disabled(self):
		self.configure(enable_lead_capture=0)
		with self.actor(self.source), self.assertRaises(frappe.PermissionError):
			capture_email(self.email)

	def test_lead_conversion_status_update(self):
		self.capture()
		name = frappe.db.get_value("Ghost Lead", {"ghost_email": self.source}, "name")
		self.convert(self.source)
		self.assertEqual(frappe.db.get_value("Ghost Lead", name, "status"), "Converted")

	def test_unverified_email_does_not_reassign_another_lead(self):
		self.capture()
		other = self.new_ghost()["user"]
		with self.actor(other):
			capture_email(self.email)
		self.assertEqual(frappe.db.count("Ghost Lead", {"captured_email": self.email}), 2)
		self.assertTrue(frappe.db.exists("Ghost Lead", {"ghost_email": self.source}))

	def test_capture_requires_source_ownership(self):
		with self.actor("Guest"), self.assertRaises(frappe.PermissionError):
			capture_email(self.email, ghost_email=self.source)

	def test_send_lead_reminders(self):
		self.capture()
		name = frappe.db.get_value("Ghost Lead", {"ghost_email": self.source}, "name")
		frappe.db.set_value("Ghost Lead", name, "creation", add_to_date(now_datetime(), hours=-25))
		with patch("frappe.sendmail") as send:
			send_lead_reminders()
		send.assert_called_once()
		self.assertEqual(frappe.db.get_value("Ghost Lead", name, "conversion_reminder_sent"), 1)
