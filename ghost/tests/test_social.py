import frappe
from frappe.tests.utils import FrappeTestCase
from ghost.api.social import convert_with_google
from ghost.api.ghost import create_ghost_session
from unittest.mock import patch, MagicMock

class TestSocialLogin(FrappeTestCase):
    def setUp(self):
        self.settings = frappe.get_single("Ghost Settings")
        self.settings.enable_ghost_feature = 1
        self.settings.enable_social_login = 1
        self.settings.google_client_id = "test-client-id"
        self.settings.verify_otp_on_conversion = 1
        self.settings.save()
        
        frappe.db.sql("DELETE FROM `tabUser` WHERE email IN ('social_ghost@guest.local', 'social_real@example.com')")
        
        session = create_ghost_session("social_ghost@guest.local")
        self.ghost_email = session["user"]
        self.real_email = "social_real@example.com"
        frappe.db.commit()

    def test_convert_with_google_fails_when_disabled(self):
        self.settings.enable_social_login = 0
        self.settings.save()
        
        with self.assertRaises(frappe.PermissionError):
            convert_with_google(self.ghost_email, "some-token")

    @patch("ghost.api.social.requests.get")
    def test_convert_with_google_success(self, mock_get):
        # Mock successful Google tokeninfo response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "email_verified": "true",
            "email": self.real_email,
            "given_name": "John",
            "family_name": "Doe"
        }
        mock_get.return_value = mock_response

        # Should bypass OTP and convert successfully
        response = convert_with_google(self.ghost_email, "valid-token")
        
        self.assertEqual(response["user"], self.real_email)
        self.assertEqual(response["conversion_mode"], "rename")
        self.assertTrue(frappe.db.exists("User", self.real_email))
        
        # Verify name was extracted
        user = frappe.get_doc("User", self.real_email)
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")

    @patch("ghost.api.social.requests.get")
    def test_convert_with_google_invalid_audience(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "wrong-client-id",
            "email_verified": "true",
            "email": self.real_email
        }
        mock_get.return_value = mock_response

        with self.assertRaises(frappe.AuthenticationError):
            convert_with_google(self.ghost_email, "valid-token")

    @patch("ghost.api.social.requests.get")
    def test_convert_with_google_unverified_email(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "email_verified": "false",
            "email": self.real_email
        }
        mock_get.return_value = mock_response

        with self.assertRaises(frappe.AuthenticationError):
            convert_with_google(self.ghost_email, "valid-token")
