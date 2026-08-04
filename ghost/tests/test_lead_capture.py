import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime
from ghost.api.lead import capture_email
from ghost.api.ghost import create_ghost_session, convert_to_real_user
from ghost.tasks import send_lead_reminders

class TestLeadCapture(FrappeTestCase):
    def setUp(self):
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.enable_lead_capture = 1
        self.settings.lead_reminder_hours = 24
        
        # Create an Email Template
        if not frappe.db.exists("Email Template", "Test Lead Reminder"):
            template = frappe.get_doc({
                "doctype": "Email Template",
                "name": "Test Lead Reminder",
                "subject": "Complete your registration",
                "response": "Hi {{ captured_email }}, come back!"
            })
            template.insert(ignore_permissions=True)
            
        self.settings.lead_reminder_email_template = "Test Lead Reminder"
        self.settings.verify_otp_on_conversion = 0
        self.settings.sandbox_mode = 0
        self.settings.save()
        
        frappe.db.sql("DELETE FROM `tabGhost Lead`")
        frappe.db.sql("DELETE FROM `tabUser` WHERE email LIKE 'lead_test_%'")
        frappe.db.commit() # nosemgrep: frappe-manual-commit - required in test harness to reset test user state

    def test_capture_email(self):
        # Create ghost user
        session = create_ghost_session("lead_test_ghost@guest.local")
        ghost_email = session["user"]
        
        # Capture email
        res = capture_email(email="lead_test_real@example.com", ghost_email=ghost_email)
        self.assertEqual(res["status"], "success")
        
        # Verify stored lead
        lead = frappe.get_last_doc("Ghost Lead", {"ghost_email": ghost_email})
        self.assertEqual(lead.captured_email, "lead_test_real@example.com")
        self.assertEqual(lead.status, "Captured")
        self.assertEqual(lead.conversion_reminder_sent, 0)
        
        # Update email
        capture_email(email="lead_test_real_new@example.com", ghost_email=ghost_email)
        lead.reload()
        self.assertEqual(lead.captured_email, "lead_test_real_new@example.com")

    def test_capture_email_disabled(self):
        self.settings.enable_lead_capture = 0
        self.settings.save()
        
        with self.assertRaises(frappe.PermissionError):
            capture_email(email="test@test.com", ghost_email="some_ghost@guest.local")

    def test_lead_conversion_status_update(self):
        # Create ghost user
        session = create_ghost_session("lead_test_conv@guest.local")
        ghost_email = session["user"]
        
        # Capture lead
        capture_email(email="lead_test_real_conv@example.com", ghost_email=ghost_email)
        
        # Convert user
        convert_to_real_user(ghost_email, "lead_test_real_conv@example.com")
        
        # Ghost Lead status should now be Converted
        # The Ghost Lead might still have the old ghost_email if rename_doc didn't update it
        # or it might have real_email. Let's just search by either or use the original `ghost_email`.
        try:
            lead = frappe.get_last_doc("Ghost Lead", {"ghost_email": ghost_email})
        except frappe.exceptions.DoesNotExistError:
            lead = frappe.get_last_doc("Ghost Lead", {"ghost_email": "lead_test_real_conv@example.com"})
        
        self.assertEqual(lead.status, "Converted")

    from unittest.mock import patch
    
    @patch("ghost.tasks.frappe.sendmail")
    def test_send_lead_reminders(self, mock_sendmail):
        # Create ghost user
        session = create_ghost_session("lead_test_rem@guest.local")
        ghost_email = session["user"]
        
        # Capture email
        capture_email(email="lead_test_rem_real@example.com", ghost_email=ghost_email)
        
        lead = frappe.get_last_doc("Ghost Lead", {"ghost_email": ghost_email})
        
        # Backdate creation to make it older than 24 hours
        old_date = add_to_date(now_datetime(), hours=-25)
        frappe.db.set_value("Ghost Lead", lead.name, "creation", old_date)
        frappe.db.commit() # nosemgrep: frappe-manual-commit - required in test harness to persist backdated timestamp for scheduler assertions
        
        # Run scheduled task
        send_lead_reminders()
        
        # Check that reminder was sent and flag updated
        lead.reload()
        self.assertEqual(lead.conversion_reminder_sent, 1)
        self.assertTrue(mock_sendmail.called)
