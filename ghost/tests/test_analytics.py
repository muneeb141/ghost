import frappe
import unittest
from frappe.utils import add_days, now_datetime

from ghost.api.ghost import convert_to_real_user, create_ghost_session
from ghost.tasks import delete_old_conversion_logs


class TestConversionAnalytics(unittest.TestCase):
	def setUp(self):
		import frappe.core.doctype.user.user as user_module
		user_module.throttle_user_creation = lambda: None

		# Ensure Ghost Role exists
		if not frappe.db.exists("Role", "Ghost"):
			frappe.get_doc({"doctype": "Role", "role_name": "Ghost"}).insert(ignore_permissions=True)

		settings = frappe.get_single("Ghost Settings")
		settings.enable_ghost_feature = 1
		settings.ghost_role = "Ghost"
		settings.verify_otp_on_conversion = 0
		settings.default_user_role = None
		settings.conversion_log_retention_days = 90
		settings.save()

		# Token generation requires a valid OAuth Client; the site's configured
		# client may not exist in test databases, so ensure one does.
		# Note: generate_oauth_tokens looks up OAuth Client by document name.
		client_id = settings.client_id
		if not client_id or not frappe.db.exists("OAuth Client", client_id):
			c = frappe.new_doc("OAuth Client")
			c.app_name = "Ghost Analytics Test"
			c.skat = "1"  # Skip Authorization
			c.default_redirect_uri = "http://localhost"
			c.redirect_uris = "http://localhost"
			c.save(ignore_permissions=True)
			client_id = c.name
		settings.client_id = client_id
		settings.save()

	def tearDown(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 0
		settings.save()

	def _convert_new_ghost(self, real_email):
		# Conversion logs are committed by convert_to_real_user, so clear any
		# stale entries from earlier test runs to keep assertions isolated.
		frappe.db.delete("Ghost Conversion Log", {"real_email": real_email})
		ghost_email = create_ghost_session()["user"]
		if frappe.db.exists("User", real_email):
			frappe.delete_doc("User", real_email, force=True)
		result = convert_to_real_user(ghost_email, real_email)
		return ghost_email, result

	def test_conversion_creates_log_when_enabled(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 1
		settings.save()

		real_email = "analytics_log_enabled@example.com"
		ghost_email, result = self._convert_new_ghost(real_email)

		self.assertEqual(result.get("conversion_mode"), "rename")
		log_name = frappe.db.exists("Ghost Conversion Log", {"real_email": real_email})
		self.assertTrue(log_name, "Conversion log entry should be created when logging is enabled")

		log = frappe.get_doc("Ghost Conversion Log", log_name)
		self.assertEqual(log.ghost_email, ghost_email)
		self.assertEqual(log.conversion_mode, "rename")
		self.assertEqual(log.conversion_channel, "OTP")
		self.assertIsNotNone(log.converted_at)
		self.assertGreaterEqual(log.conversion_duration_ms, 0)
		print(f"\n[Success] Logged conversion {ghost_email} -> {real_email}")

	def test_no_log_when_disabled(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 0
		settings.save()

		real_email = "analytics_log_disabled@example.com"
		ghost_email, result = self._convert_new_ghost(real_email)

		self.assertEqual(result.get("conversion_mode"), "rename")
		self.assertFalse(
			frappe.db.exists("Ghost Conversion Log", {"real_email": real_email}),
			"No conversion log entry should be created when logging is disabled",
		)
		print(f"\n[Success] No log written for {ghost_email} -> {real_email} with logging disabled")

	def test_delete_old_conversion_logs(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 1
		settings.conversion_log_retention_days = 90
		settings.save()

		old_log = frappe.get_doc({
			"doctype": "Ghost Conversion Log",
			"ghost_email": "ghost_old@guest.local",
			"real_email": "old_conversion@example.com",
			"conversion_mode": "rename",
			"conversion_duration_ms": 10,
			"converted_at": now_datetime(),
		}).insert(ignore_permissions=True)
		# Backdate beyond retention window
		frappe.db.set_value(
			"Ghost Conversion Log", old_log.name, "converted_at",
			add_days(now_datetime(), -120), update_modified=False,
		)

		recent_log = frappe.get_doc({
			"doctype": "Ghost Conversion Log",
			"ghost_email": "ghost_recent@guest.local",
			"real_email": "recent_conversion@example.com",
			"conversion_mode": "manual_migration",
			"conversion_duration_ms": 25,
			"converted_at": now_datetime(),
		}).insert(ignore_permissions=True)

		delete_old_conversion_logs()

		self.assertFalse(
			frappe.db.exists("Ghost Conversion Log", old_log.name),
			"Log older than retention should be deleted",
		)
		self.assertTrue(
			frappe.db.exists("Ghost Conversion Log", recent_log.name),
			"Recent log should be kept",
		)
		print("\n[Success] Cleanup deleted old logs and kept recent ones")

	def test_cleanup_skipped_when_logging_disabled(self):
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 0
		settings.save()

		old_log = frappe.get_doc({
			"doctype": "Ghost Conversion Log",
			"ghost_email": "ghost_kept@guest.local",
			"real_email": "kept_conversion@example.com",
			"conversion_mode": "rename",
			"conversion_duration_ms": 10,
			"converted_at": now_datetime(),
		}).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Ghost Conversion Log", old_log.name, "converted_at",
			add_days(now_datetime(), -120), update_modified=False,
		)

		delete_old_conversion_logs()

		self.assertTrue(
			frappe.db.exists("Ghost Conversion Log", old_log.name),
			"Cleanup must not run when conversion logging is disabled",
		)
		frappe.delete_doc("Ghost Conversion Log", old_log.name, force=True)
		print("\n[Success] Cleanup respected disabled logging setting")

	def test_analytics_dashboard_endpoint_and_channels(self):
		from ghost.ghost.page.ghost_analytics.ghost_analytics import get_analytics_data
		settings = frappe.get_single("Ghost Settings")
		settings.enable_conversion_logging = 1
		settings.save()

		real_email = "analytics_channel_test@example.com"
		frappe.db.delete("Ghost Conversion Log", {"real_email": real_email})
		ghost_email = create_ghost_session()["user"]
		if frappe.db.exists("User", real_email):
			frappe.delete_doc("User", real_email, force=True)

		convert_to_real_user(ghost_email, real_email, conversion_channel="Magic Link")

		log_name = frappe.db.exists("Ghost Conversion Log", {"real_email": real_email})
		log = frappe.get_doc("Ghost Conversion Log", log_name)
		self.assertEqual(log.conversion_channel, "Magic Link")

		frappe.set_user("Administrator")
		data = get_analytics_data()
		self.assertIn("conversions_by_channel", data)
		self.assertIn("reminder_recovery_rate", data)
		self.assertIn("total_merged_ghosts", data)
		channels = {row["channel"]: row["count"] for row in data["conversions_by_channel"]}
		self.assertIn("Magic Link", channels)
		print("\n[Success] Verified get_analytics_data returns channel breakdown and recovery stats")
