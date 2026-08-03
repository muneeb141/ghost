import frappe
from frappe.tests.utils import FrappeTestCase
from ghost.api.ghost import create_ghost_session, convert_to_real_user

class TestMultiDeviceMerge(FrappeTestCase):
    def setUp(self):
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.enable_multi_device_merge = 1
        self.settings.merge_detection_method = "Lead Email"
        self.settings.verify_otp_on_conversion = 0
        self.settings.save()
        
        frappe.db.sql("DELETE FROM `tabUser` WHERE email LIKE 'merge_test_%'")
        if frappe.db.exists("DocType", "Ghost Lead"):
            frappe.db.sql("DELETE FROM `tabGhost Lead` WHERE captured_email = 'merge_test_real@example.com'")
        frappe.db.commit()

    def test_merge_related_ghosts(self):
        # 1. Create main ghost
        session1 = create_ghost_session("merge_test_ghost1@guest.local")
        ghost1 = session1["user"]
        
        # 2. Create another ghost that also has the same lead email
        session2 = create_ghost_session("merge_test_ghost2@guest.local")
        ghost2 = session2["user"]
        
        # Fake a lead capture for ghost2 (since Ghost Lead doctype might not exist in this isolated branch,
        # we will only test it if it exists, otherwise we mock `find_related_ghosts`)
        from unittest.mock import patch
        with patch('ghost.api.merge.find_related_ghosts') as mock_find:
            mock_find.return_value = [ghost2]
            
            # 3. Convert ghost1
            response = convert_to_real_user(ghost1, "merge_test_real@example.com")
            
            # It should have merged ghost2
            self.assertEqual(response["user"], "merge_test_real@example.com")
            self.assertIn("merged_ghosts", response)
            self.assertEqual(response["merged_count"], 1)
            self.assertEqual(response["merged_ghosts"], [ghost2])
            
            # Verify ghost2 is deleted
            self.assertFalse(frappe.db.exists("User", ghost2))
            
            # Verify ghost1 is deleted/renamed
            self.assertFalse(frappe.db.exists("User", ghost1))
            self.assertTrue(frappe.db.exists("User", "merge_test_real@example.com"))

    def test_merge_disabled(self):
        self.settings.enable_multi_device_merge = 0
        self.settings.save()
        
        session1 = create_ghost_session("merge_test_disabled1@guest.local")
        ghost1 = session1["user"]
        
        session2 = create_ghost_session("merge_test_disabled2@guest.local")
        ghost2 = session2["user"]
        
        from unittest.mock import patch
        with patch('ghost.api.merge.find_related_ghosts') as mock_find:
            mock_find.return_value = [ghost2]
            
            response = convert_to_real_user(ghost1, "merge_test_real_disabled@example.com")
            
            # It should NOT have merged ghost2 because toggle is off
            self.assertNotIn("merged_ghosts", response)
            
            # ghost2 should still exist
            self.assertTrue(frappe.db.exists("User", ghost2))
