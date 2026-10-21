from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime

from ghost.tasks import _clear_expired_sessions, delete_expired_ghost_users, expire_otps
from ghost.tests.helpers import GhostIntegrationCase


class TestGhostTasks(GhostIntegrationCase):
	def test_delete_expired_ghost_users_uses_native_cleanup(self):
		self.configure(enable_auto_cleanup=1, expiration_days=30, cleanup_batch_size=500)
		data = self.new_ghost()
		old = data["user"]
		frappe.db.set_value("User", old, "creation", add_days(now_datetime(), -40))
		delete_expired_ghost_users()
		self.assertFalse(frappe.db.exists("OAuth Bearer Token", data["access_token"]))
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

	def test_cleanup_never_deletes_a_caller_named_account_on_the_ghost_domain(self):
		self.configure(enable_auto_cleanup=1)
		user = self.new_user(email="person@" + self.settings.ghost_email_domain, role="Ghost")
		frappe.db.set_value("User", user.name, "creation", add_days(now_datetime(), -40))
		delete_expired_ghost_users()
		self.assertTrue(frappe.db.exists("User", user.name))
		self.assertEqual(frappe.db.get_value("User", user.name, "enabled"), 1)

	def test_cleanup_never_deletes_staff_with_an_anonymous_looking_name(self):
		self.configure(enable_auto_cleanup=1)
		user = self.new_ghost()["user"]
		frappe.db.set_value(
			"User", user, {"creation": add_days(now_datetime(), -40), "user_type": "System User"}
		)
		delete_expired_ghost_users()
		self.assertTrue(frappe.db.exists("User", user))
		self.assertEqual(frappe.db.get_value("User", user, "enabled"), 1)

	def test_cleanup_retains_native_links_and_expires_linked_identity_credentials(self):
		self.configure(enable_auto_cleanup=1)
		data = self.new_ghost()
		lead = frappe.get_doc(
			{
				"doctype": "Ghost Lead",
				"ghost_email": data["user"],
				"captured_email": self.email,
				"status": "Captured",
			}
		).insert()
		frappe.db.set_value("User", data["user"], "creation", add_days(now_datetime(), -40))
		delete_expired_ghost_users()
		self.assertTrue(frappe.db.exists("User", data["user"]))
		self.assertEqual(frappe.db.get_value("Ghost Lead", lead.name, "ghost_email"), data["user"])
		self.assertEqual(frappe.db.get_value("User", data["user"], "enabled"), 0)
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", data["access_token"], "status"), "Revoked")

	def test_cleanup_does_not_commit_the_callers_transaction(self):
		self.configure(enable_auto_cleanup=1)
		data = self.new_ghost()
		frappe.db.set_value("User", data["user"], "creation", add_days(now_datetime(), -40))
		frappe.db.savepoint("before_cleanup")
		delete_expired_ghost_users()
		self.assertFalse(frappe.db.exists("User", data["user"]))
		frappe.db.rollback(save_point="before_cleanup")
		self.assertTrue(frappe.db.exists("User", data["user"]))
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", data["access_token"], "status"), "Active")

	def test_linked_cleanup_with_a_session_does_not_commit_before_job_completion(self):
		self.configure(enable_auto_cleanup=1)
		data = self.new_ghost()
		frappe.get_doc(
			{
				"doctype": "Ghost Lead",
				"ghost_email": data["user"],
				"captured_email": self.email,
				"status": "Captured",
			}
		).insert()
		frappe.db.set_value("User", data["user"], "creation", add_days(now_datetime(), -40))
		sessions = frappe.qb.DocType("Sessions")
		frappe.qb.into(sessions).columns("sid", "user", "lastupdate").insert(
			self.tag, data["user"], now_datetime()
		).run()
		frappe.db.savepoint("before_linked_cleanup")
		delete_expired_ghost_users()
		self.assertEqual(frappe.db.get_value("User", data["user"], "enabled"), 0)
		frappe.db.rollback(save_point="before_linked_cleanup")
		self.assertEqual(frappe.db.get_value("User", data["user"], "enabled"), 1)
		self.assertEqual(frappe.db.get_value("OAuth Bearer Token", data["access_token"], "status"), "Active")
		# A deferred callback must not log out a user whose expiry was rolled back.
		with patch("frappe.sessions.clear_sessions") as clear:
			_clear_expired_sessions(data["user"])
		clear.assert_not_called()
