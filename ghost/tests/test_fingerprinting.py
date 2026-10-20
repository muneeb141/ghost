import frappe
from frappe.utils import now_datetime

from ghost.tests.helpers import GhostIntegrationCase


class TestSessionFingerprinting(GhostIntegrationCase):
	def test_same_fingerprint_always_creates_distinct_identities(self):
		self.configure(enable_fingerprinting=1)
		a = self.new_ghost(fingerprint=self.tag)
		b = self.new_ghost(fingerprint=self.tag)
		self.assertNotEqual(a["user"], b["user"])

	def test_legacy_fingerprint_is_not_an_authentication_credential(self):
		self.configure(enable_fingerprinting=1)
		a = self.new_ghost()
		row = frappe.get_doc(
			{
				"doctype": "Ghost Fingerprint",
				"fingerprint": self.tag,
				"ghost_email": a["user"],
				"last_seen": now_datetime(),
			}
		).insert()
		b = self.new_ghost(fingerprint=self.tag)
		self.assertNotEqual(a["user"], b["user"])
		self.assertEqual(row.reload().ghost_email, a["user"])

	def test_disabled_fingerprinting_ignores_fingerprint(self):
		self.configure(enable_fingerprinting=0)
		a = self.new_ghost(fingerprint=self.tag)
		b = self.new_ghost(fingerprint=self.tag)
		self.assertNotEqual(a["user"], b["user"])
		self.assertFalse(frappe.db.exists("Ghost Fingerprint", {"fingerprint": self.tag}))
