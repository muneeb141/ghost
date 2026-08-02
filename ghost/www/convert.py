import frappe
from frappe.utils import now_datetime

def get_context(context):
    token = frappe.form_dict.get("token")
    if not token:
        context.error_message = "No token provided."
        return context

    settings = frappe.get_single("Ghost Settings")
    if not settings.enable_magic_link:
        context.error_message = "Magic Link feature is disabled."
        return context

    token_doc_name = frappe.db.get_value(
        "Ghost Magic Link Token",
        {
            "token": token,
            "status": "Pending"
        },
        "name"
    )

    if not token_doc_name:
        context.error_message = "Invalid or already used token."
        return context

    token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)

    if token_doc.expires_on < now_datetime():
        token_doc.db_set("status", "Expired")
        context.error_message = "This magic link has expired."
        return context

    # Valid token. We can call convert_to_real_user directly.
    # Wait, convert_to_real_user needs ghost_email and real_email.
    from ghost.api.ghost import convert_to_real_user
    
    try:
        # Mark used
        token_doc.db_set("status", "Used")
        
        # In convert_to_real_user, the OTP verification is normally required. 
        # But wait, we are already verified by the magic link.
        # We need a way to bypass OTP verification for magic link conversions.
        # Let's pass a special flag or handle it.
        # Actually, if we just call it and it checks for OTP, it will fail.
        # We need to modify ghost.api.ghost.convert_to_real_user to allow a bypass if `bypass_otp=True`.
        response = convert_to_real_user(
            ghost_email=token_doc.ghost_email,
            real_email=token_doc.real_email,
            bypass_otp=True
        )
        
        # If magic link redirect URL is configured, redirect to it with tokens in hash
        if settings.magic_link_redirect_url:
            frappe.local.flags.redirect_location = f"{settings.magic_link_redirect_url}#access_token={response['access_token']}&refresh_token={response['refresh_token']}"
            raise frappe.Redirect
            
        context.success = True
        context.response = response
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Magic Link Conversion failed: {str(e)}")
        context.error_message = "An error occurred during conversion."

    return context
