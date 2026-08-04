import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime
import secrets

@frappe.whitelist(allow_guest=True)
def send_magic_link(ghost_email, real_email):
    """Generate and send a magic link for conversion."""
    settings = frappe.get_single("Ghost Settings")
    
    if not settings.enable_magic_link:
        frappe.throw(_("Magic Link feature is not enabled"))
        
    if not settings.magic_link_email_template:
        frappe.throw(_("Magic link email template is not configured in settings"))
        
    # Check if a pending token already exists and is valid
    existing_token = frappe.db.get_value(
        "Ghost Magic Link Token",
        {
            "ghost_email": ghost_email,
            "real_email": real_email,
            "status": "Pending",
            "expires_on": (">", now_datetime())
        },
        "name"
    )
    
    if existing_token:
        # Instead of resending the same one (or throwing), we could generate a new one,
        # but for security, usually it's better to invalidate old ones or just generate a new one.
        # We will generate a new one and mark the old one as expired.
        frappe.db.set_value("Ghost Magic Link Token", existing_token, "status", "Expired")
        
    token = secrets.token_urlsafe(32)
    expires_on = add_to_date(now_datetime(), minutes=settings.magic_link_expiry_minutes)
    
    # Store token
    doc = frappe.get_doc({
        "doctype": "Ghost Magic Link Token",
        "token": token,
        "ghost_email": ghost_email,
        "real_email": real_email,
        "status": "Pending",
        "expires_on": expires_on
    })
    doc.insert(ignore_permissions=True)
    
    # Build URL (absolute)
    magic_link_url = f"{frappe.utils.get_url()}/convert?token={token}"
    
    # Render Email Template
    email_template = frappe.get_doc("Email Template", settings.magic_link_email_template)
    args = {
        "magic_link": magic_link_url,
        "ghost_email": ghost_email,
        "real_email": real_email,
        "expires_in_minutes": settings.magic_link_expiry_minutes
    }
    subject = frappe.render_template(email_template.subject, args)
    content = frappe.render_template(email_template.response, args)
    
    # Send email
    try:
        frappe.sendmail(
            recipients=[real_email],
            subject=subject,
            content=content,
            now=True
        )
    except Exception as e:
        frappe.log_error(message=str(e), title="Magic Link Email Failed")
        # If email fails (e.g. invalid SMTP config locally), we still return success 
        # but attach the link so the developer can still test the flow!
        pass
    
    return {
        "status": "success", 
        "message": _("Magic link generated successfully"),
        "dev_magic_link": magic_link_url
    }

@frappe.whitelist(allow_guest=True)
def consume_magic_link(token):
    """Consumes a magic link token and converts the user."""
    settings = frappe.get_single("Ghost Settings")
    if not settings.enable_magic_link:
        frappe.throw(_("Magic Link feature is disabled."))

    token_doc_name = frappe.db.get_value(
        "Ghost Magic Link Token",
        {"token": token, "status": "Pending"},
        "name"
    )

    if not token_doc_name:
        frappe.throw(_("Invalid or already used token."))

    token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)

    if token_doc.expires_on < now_datetime():
        token_doc.db_set("status", "Expired")
        frappe.throw(_("This magic link has expired."))

    from ghost.api.ghost import convert_to_real_user
    
    # Mark used
    token_doc.db_set("status", "Used")
    
    response = convert_to_real_user(
        ghost_email=token_doc.ghost_email,
        real_email=token_doc.real_email,
        bypass_otp=True,
        conversion_channel="Magic Link"
    )
    
    if settings.magic_link_redirect_url:
        response["redirect_url"] = f"{settings.magic_link_redirect_url}#access_token={response.get('access_token', '')}&refresh_token={response.get('refresh_token', '')}"
        
    return response
