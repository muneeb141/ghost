import frappe
from frappe.tests.utils import FrappeTestCase
from ghost.api.magic_link import send_magic_link
from ghost.api.ghost import create_ghost_session
from ghost.www.convert import get_context
from frappe.utils import now_datetime, add_to_date

class TestMagicLink(FrappeTestCase):
    def setUp(self):
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.enable_magic_link = 1
        self.settings.magic_link_expiry_minutes = 30
        
        # We need an email template for testing
        if not frappe.db.exists("Email Template", "Test Magic Link"):
            frappe.get_doc({
                "doctype": "Email Template",
                "name": "Test Magic Link",
                "subject": "Your Magic Link",
                "response": "Click here: {{ magic_link }}"
            }).insert(ignore_permissions=True)
            
        self.settings.magic_link_email_template = "Test Magic Link"
        self.settings.verify_otp_on_conversion = 1
        self.settings.save()
        
        # Clear out old test users
        frappe.db.sql("DELETE FROM `tabUser` WHERE email IN ('magic_ghost@guest.local', 'magic_real@example.com')")
        
        session = create_ghost_session("magic_ghost@guest.local")
        self.ghost_email = session["user"]
        self.real_email = "magic_real@example.com"
        
        frappe.db.commit()

    def test_send_magic_link_fails_when_disabled(self):
        self.settings.enable_magic_link = 0
        self.settings.save()
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            send_magic_link(self.ghost_email, self.real_email)

    def test_send_magic_link_generates_token(self):
        response = send_magic_link(self.ghost_email, self.real_email)
        self.assertEqual(response["status"], "success")
        
        # Verify token doc was created
        token_doc_name = frappe.db.get_value(
            "Ghost Magic Link Token",
            {"ghost_email": self.ghost_email, "real_email": self.real_email, "status": "Pending"}
        )
        self.assertTrue(token_doc_name)
        
        token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)
        self.assertIsNotNone(token_doc.token)

    def test_convert_magic_link_success(self):
        # Generate token
        send_magic_link(self.ghost_email, self.real_email)
        token_doc_name = frappe.db.get_value(
            "Ghost Magic Link Token",
            {"ghost_email": self.ghost_email, "status": "Pending"}
        )
        token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)
        
        # Simulate click
        frappe.form_dict = {"token": token_doc.token}
        
        # Need a mock context
        class MockContext:
            error_message = None
            is_valid = False
            token = None
            
        context = MockContext()
        get_context(context)
        self.assertTrue(getattr(context, "is_valid", False))
        
        from ghost.api.magic_link import consume_magic_link
        res = consume_magic_link(token_doc.token)
        self.assertEqual(res["user"], self.real_email)
        self.assertEqual(res["conversion_mode"], "rename")
        
        # Check token is marked as Used
        token_doc.reload()
        self.assertEqual(token_doc.status, "Used")
        
        # Check bypass worked (verify_otp_on_conversion was 1, but we didn't provide OTP)
        # Verify the user actually converted
        self.assertFalse(frappe.db.exists("User", self.ghost_email))
        self.assertTrue(frappe.db.exists("User", self.real_email))

    def test_convert_magic_link_expired(self):
        send_magic_link(self.ghost_email, "magic_expired@example.com")
        token_doc_name = frappe.db.get_value(
            "Ghost Magic Link Token",
            {"ghost_email": self.ghost_email, "status": "Pending"}
        )
        token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)
        
        # Manually expire it
        token_doc.db_set("expires_on", add_to_date(now_datetime(), minutes=-10))
        
        frappe.form_dict = {"token": token_doc.token}
        
        class MockContext:
            error_message = None
            success = False
            response = None
            
        context = MockContext()
        get_context(context)
        
        self.assertFalse(context.success)
        self.assertEqual(context.error_message, "This magic link has expired.")
        
        token_doc.reload()
        self.assertEqual(token_doc.status, "Expired")
