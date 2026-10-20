import frappe

from ghost.api.analytics import get_conversion_funnel
from ghost.tests.helpers import GhostIntegrationCase


class TestAnalyticsAPI(GhostIntegrationCase):
	def test_api_fails_when_disabled(self):
		with self.assertRaises(frappe.ValidationError):
			get_conversion_funnel()

	def test_api_fails_without_system_manager_role(self):
		self.configure(enable_analytics_api=1)
		user = self.new_user()
		with self.actor(user.name), self.assertRaises(frappe.PermissionError):
			get_conversion_funnel()

	def test_api_succeeds_when_enabled(self):
		self.configure(enable_analytics_api=1)
		result = get_conversion_funnel()
		self.assertEqual(result["status"], "success")
		self.assertIn("total_sessions", result["data"]["metrics"])
		self.assertIn("lead_recovery", result["data"]["metrics"])
		self.assertIn("conversions_by_channel", result["data"]["breakdowns"])
