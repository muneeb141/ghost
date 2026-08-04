import frappe
import unittest
from frappe.utils import add_days, now_datetime
from ghost.tasks import delete_expired_ghost_users

class TestGhostTasks(unittest.TestCase):
    def setUp(self):
        # Ensure Ghost Role exists
        if not frappe.db.exists("Role", "Ghost"):
            frappe.get_doc({"doctype": "Role", "role_name": "Ghost"}).insert(ignore_permissions=True)

        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.enable_auto_cleanup = 1
        self.settings.ghost_role = "Ghost"
        self.settings.ghost_email_domain = "guest.local"
        self.settings.expiration_days = 30
        self.settings.cleanup_batch_size = 500
        self.settings.save()

    def test_delete_expired_ghost_users_bulk(self):
        # Create a dummy expired ghost user
        expired_ghost_email = "ghost_expired_123@guest.local"
        
        # Delete if exists from previous failed test
        if frappe.db.exists("User", expired_ghost_email):
            frappe.delete_doc("User", expired_ghost_email, force=1)
            
        user = frappe.get_doc({
            "doctype": "User",
            "email": expired_ghost_email,
            "first_name": "Expired",
            "last_name": "Ghost",
            "send_welcome_email": 0,
            "roles": [{"role": "Ghost"}]
        }).insert(ignore_permissions=True)
        
        # Manually backdate creation date
        past_date = add_days(now_datetime(), -40)
        frappe.db.set_value("User", user.name, "creation", past_date, update_modified=False)
        
        # Run cleanup task
        delete_expired_ghost_users()
        
        # Assert user is deleted
        self.assertFalse(frappe.db.exists("User", user.name))
        
        # Assert child tables are cleaned up
        has_role = frappe.db.exists("Has Role", {"parent": user.name})
        self.assertFalse(has_role)

    def test_does_not_delete_recent_ghost_users(self):
        recent_ghost_email = "ghost_recent_456@guest.local"
        
        if frappe.db.exists("User", recent_ghost_email):
            frappe.delete_doc("User", recent_ghost_email, force=1)
            
        user = frappe.get_doc({
            "doctype": "User",
            "email": recent_ghost_email,
            "first_name": "Recent",
            "last_name": "Ghost",
            "send_welcome_email": 0,
            "roles": [{"role": "Ghost"}]
        }).insert(ignore_permissions=True)
        
        # Backdate only slightly (less than 30 days)
        past_date = add_days(now_datetime(), -10)
        frappe.db.set_value("User", user.name, "creation", past_date, update_modified=False)
        
        # Run cleanup task
        delete_expired_ghost_users()
        
        # Assert user is NOT deleted
        self.assertTrue(frappe.db.exists("User", user.name))
        
        # Clean up manually
        frappe.delete_doc("User", user.name, force=1)
