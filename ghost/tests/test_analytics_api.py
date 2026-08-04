import frappe
import unittest
from ghost.api.analytics import get_conversion_funnel

class TestAnalyticsAPI(unittest.TestCase):
    def setUp(self):
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_analytics_api = 1
        self.settings.save()
        
        # We need to simulate being a System Manager for the success tests
        # frappe.set_user("Administrator") has System Manager role by default
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_analytics_api = 0
        self.settings.save()

    def test_api_fails_when_disabled(self):
        self.settings.enable_analytics_api = 0
        self.settings.save()
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            get_conversion_funnel()

    def test_api_fails_without_system_manager_role(self):
        # Create a test user without System Manager role
        test_user = "test_no_role@example.com"
        if not frappe.db.exists("User", test_user):
            user = frappe.get_doc({
                "doctype": "User",
                "email": test_user,
                "first_name": "Test No Role"
            }).insert(ignore_permissions=True)
            # Ensure they don't have System Manager
            frappe.db.sql("DELETE FROM `tabHas Role` WHERE parent=%s AND role='System Manager'", test_user)
            
        frappe.set_user(test_user)
        
        with self.assertRaises(frappe.PermissionError):
            get_conversion_funnel()

    def test_api_succeeds_when_enabled(self):
        response = get_conversion_funnel()
        self.assertEqual(response.get("status"), "success")
        self.assertIn("data", response)
        self.assertIn("metrics", response["data"])
        self.assertIn("total_sessions", response["data"]["metrics"])
        self.assertIn("total_conversions", response["data"]["metrics"])
        self.assertIn("conversion_rate", response["data"]["metrics"])
        self.assertIn("avg_time_to_convert_ms", response["data"]["metrics"])
        self.assertIn("total_merged_sessions", response["data"]["metrics"])
        self.assertIn("lead_recovery", response["data"]["metrics"])
        self.assertIn("breakdowns", response["data"])
        self.assertIn("conversions_by_mode", response["data"]["breakdowns"])
        self.assertIn("conversions_by_channel", response["data"]["breakdowns"])
        self.assertIn("daily_conversions", response["data"]["breakdowns"])
        print("\n[Success] Funnel REST API returned enriched growth metrics")
