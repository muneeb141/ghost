import frappe
from frappe import _
import requests

@frappe.whitelist(allow_guest=True)
@frappe.rate_limiter.rate_limit(limit=10, seconds=60)
def convert_with_google(ghost_email, id_token):
    """
    Verify Google ID token and convert the ghost session to the Google user's email.
    """
    settings = frappe.get_single("Ghost Settings")
    
    if not settings.enable_social_login:
        frappe.throw(_("Social Login is not enabled"), frappe.PermissionError)
        
    if not settings.google_client_id:
        frappe.throw(_("Google Client ID is not configured"))
        
    if not ghost_email or not id_token:
        frappe.throw(_("Ghost email and Google ID token are required"))
        
    try:
        # Verify the ID token using Google's public tokeninfo endpoint
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10
        )
        
        if response.status_code != 200:
            frappe.log_error(f"Google Token Verification Failed: {response.text}", "Social Login Error")
            frappe.throw(_("Invalid Google ID Token"), frappe.AuthenticationError)
            
        token_info = response.json()
        
        # Verify audience
        if token_info.get("aud") != settings.google_client_id:
            frappe.throw(_("Invalid Google Client ID Audience"), frappe.AuthenticationError)
            
        # Verify email verified
        if token_info.get("email_verified") not in ("true", True):
            frappe.throw(_("Google account email is not verified"), frappe.AuthenticationError)
            
        real_email = token_info.get("email")
        if not real_email:
            frappe.throw(_("Email not provided by Google"), frappe.AuthenticationError)
            
        first_name = token_info.get("given_name")
        last_name = token_info.get("family_name")
        
        # Bypass OTP because Google verified them
        from ghost.api.ghost import convert_to_real_user
        
        conversion_result = convert_to_real_user(
            ghost_email=ghost_email,
            real_email=real_email,
            first_name=first_name,
            last_name=last_name,
            bypass_otp=True
        )
        
        return conversion_result
        
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Failed to communicate with Google: {str(e)}", "Social Login Error")
        frappe.throw(_("Could not verify token with Google. Please try again later."))
