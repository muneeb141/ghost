import frappe
from frappe.utils import add_days, now_datetime

from ghost.ghost.page.ghost_analytics.ghost_analytics import get_analytics_data
from ghost.tasks import delete_old_conversion_logs
from ghost.tests.helpers import GhostIntegrationCase


class TestConversionAnalytics(GhostIntegrationCase):
	def log(self, channel="OTP", days=0):
		return frappe.get_doc(
			{
				"doctype": "Ghost Conversion Log",
				"ghost_email": f"ghost_{self.tag}@{self.settings.ghost_email_domain}",
				"real_email": self.email,
				"conversion_mode": "rename",
				"conversion_channel": channel,
				"conversion_duration_ms": 10,
				"converted_at": add_days(now_datetime(), days),
			}
		).insert()

	def test_conversion_creates_log_when_enabled(self):
		self.configure(enable_conversion_logging=1)
		source = self.new_ghost()["user"]
		self.convert(source)
		name = frappe.db.get_value("Ghost Conversion Log", {"real_email": self.email}, "name")
		log = frappe.get_doc("Ghost Conversion Log", name)
		self.assertEqual(log.ghost_email, source)
		self.assertEqual(log.conversion_channel, "OTP")
		self.assertGreaterEqual(log.conversion_duration_ms, 0)

	def test_no_log_when_disabled(self):
		source = self.new_ghost()["user"]
		self.convert(source)
		self.assertFalse(frappe.db.exists("Ghost Conversion Log", {"real_email": self.email}))

	def test_delete_old_conversion_logs(self):
		self.configure(enable_conversion_logging=1, conversion_log_retention_days=90)
		old = self.log(days=-120)
		recent = self.log()
		delete_old_conversion_logs()
		self.assertFalse(frappe.db.exists("Ghost Conversion Log", old.name))
		self.assertTrue(frappe.db.exists("Ghost Conversion Log", recent.name))

	def test_cleanup_skipped_when_logging_disabled(self):
		old = self.log(days=-120)
		delete_old_conversion_logs()
		self.assertTrue(frappe.db.exists("Ghost Conversion Log", old.name))

	def test_analytics_dashboard_endpoint_and_channels(self):
		self.log(channel="Magic Link")
		data = get_analytics_data()
		self.assertIn("Magic Link", [row["channel"] for row in data["conversions_by_channel"]])
		self.assertIn("reminder_recovery_rate", data)
		self.assertIn("total_merged_ghosts", data)
