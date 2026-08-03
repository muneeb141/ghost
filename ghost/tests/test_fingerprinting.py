import frappe
import unittest
from ghost.api.ghost import create_ghost_session
from frappe.utils import add_days, now_datetime

class TestSessionFingerprinting(unittest.TestCase):
    def setUp(self):
        # Ensure Ghost Role exists
        if not frappe.db.exists("Role", "Ghost"):
            frappe.get_doc({"doctype": "Role", "role_name": "Ghost"}).insert(ignore_permissions=True)

        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.ghost_role = "Ghost"
        self.settings.ghost_email_domain = "guest.local"
        self.settings.enable_fingerprinting = 1
        self.settings.fingerprint_expiry_days = 7
        self.settings.save()

    def test_fingerprint_creates_and_returns_same_user(self):
        fingerprint = "test_fp_12345"
        
        # Cleanup
        fp_name = frappe.db.exists("Ghost Fingerprint", {"fingerprint": fingerprint})
        if fp_name:
            frappe.delete_doc("Ghost Fingerprint", fp_name, force=1)
            
        # First call creates a new user
        res1 = create_ghost_session(fingerprint=fingerprint)
        email1 = res1.get("user")
        
        self.assertTrue(email1.startswith("ghost_"))
        
        # Second call with same fingerprint should return same user
        res2 = create_ghost_session(fingerprint=fingerprint)
        email2 = res2.get("user")
        
        self.assertEqual(email1, email2)
        self.assertEqual(res2.get("message"), "Reconnected to existing Ghost session")

    def test_expired_fingerprint_creates_new_user(self):
        fingerprint = "test_fp_expired"
        
        # Cleanup
        fp_name = frappe.db.exists("Ghost Fingerprint", {"fingerprint": fingerprint})
        if fp_name:
            frappe.delete_doc("Ghost Fingerprint", fp_name, force=1)
            
        res1 = create_ghost_session(fingerprint=fingerprint)
        email1 = res1.get("user")
        
        # Manually expire the fingerprint
        fp_name = frappe.db.exists("Ghost Fingerprint", {"fingerprint": fingerprint})
        past_date = add_days(now_datetime(), -10)
        frappe.db.set_value("Ghost Fingerprint", fp_name, "last_seen", past_date, update_modified=False)
        
        # Second call should ignore expired fingerprint and create new user
        res2 = create_ghost_session(fingerprint=fingerprint)
        email2 = res2.get("user")
        
        self.assertNotEqual(email1, email2)
        self.assertEqual(res2.get("message"), "Ghost session created")
        
        # Verify the fingerprint is now linked to the new email
        updated_fp = frappe.get_doc("Ghost Fingerprint", fp_name)
        self.assertEqual(updated_fp.ghost_email, email2)

    def test_disabled_fingerprinting_ignores_fingerprint(self):
        self.settings.enable_fingerprinting = 0
        self.settings.save()
        
        fingerprint = "test_fp_disabled"
        
        res1 = create_ghost_session(fingerprint=fingerprint)
        email1 = res1.get("user")
        
        res2 = create_ghost_session(fingerprint=fingerprint)
        email2 = res2.get("user")
        
        self.assertNotEqual(email1, email2)
        self.assertFalse(frappe.db.exists("Ghost Fingerprint", {"fingerprint": fingerprint}))
