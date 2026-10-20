import frappe
from frappe.utils import add_days, now_datetime

from ghost.tasks import delete_expired_ghost_users, expire_otps
from ghost.tests.helpers import GhostIntegrationCase


class TestGhostTasks(GhostIntegrationCase):
	def test_delete_expired_ghost_users_bulk(self):
		self.configure(enable_auto_cleanup=1, expiration_days=30, cleanup_batch_size=500)
		old = self.new_ghost()["user"]
		frappe.db.set_value("User", old, "creation", add_days(now_datetime(), -40))
		delete_expired_ghost_users()
		self.assertFalse(frappe.db.exists("User", old))
		self.assertFalse(frappe.db.exists("Has Role", {"parent": old}))

	def test_does_not_delete_recent_ghost_users(self):
		self.configure(enable_auto_cleanup=1, expiration_days=30)
		recent = self.new_ghost()["user"]
		delete_expired_ghost_users()
		self.assertTrue(frappe.db.exists("User", recent))

	def test_cleanup_disabled(self):
		self.configure(enable_auto_cleanup=0)
		old = self.new_ghost()["user"]
		frappe.db.set_value("User", old, "creation", add_days(now_datetime(), -40))
		delete_expired_ghost_users()
		self.assertTrue(frappe.db.exists("User", old))

	def test_scheduler_expires_elapsed_codes(self):
		self.code()
		name = frappe.db.get_value("Ghost OTP", {"email": self.email}, "name")
		frappe.db.set_value("Ghost OTP", name, "expiry", add_days(now_datetime(), -1))
		expire_otps()
		self.assertEqual(frappe.db.get_value("Ghost OTP", name, "status"), "Expired")
