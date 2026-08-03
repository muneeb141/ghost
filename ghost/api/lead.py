import frappe
from frappe import _

@frappe.whitelist()
def capture_email(email, ghost_email=None):
    """
    Capture a ghost user's email before full conversion.
    Allows for abandoned session recovery.
    """
    settings = frappe.get_single("Ghost Settings")
    if not settings.enable_lead_capture:
        frappe.throw(_("Lead Capture is not enabled"), frappe.PermissionError)
        
    if not ghost_email:
        ghost_email = frappe.session.user
        
    if not ghost_email or ghost_email == "Guest" or not email:
        frappe.throw(_("Both ghost_email and email are required"))
        
    if not frappe.db.exists("User", ghost_email):
        frappe.throw(_("Invalid Ghost User"))
        
    # Get dynamic mapping config
    lead_dt = settings.lead_doctype or "Ghost Lead"
    email_field = settings.lead_email_fieldname or "captured_email"
    ghost_field = settings.lead_ghost_fieldname or "ghost_email"
    status_field = settings.lead_status_fieldname or "status"
    captured_status = settings.lead_captured_status or "Captured"
    
    # Check if this ghost user already captured an email
    existing_lead = frappe.db.get_value(lead_dt, {ghost_field: ghost_email}, "name")
    if existing_lead:
        # Update the captured email if it changed
        frappe.db.set_value(lead_dt, existing_lead, email_field, email)
        return {"status": "success", "message": _("Lead updated successfully")}
        
    # Create new lead
    lead = frappe.new_doc(lead_dt)
    lead.set(ghost_field, ghost_email)
    lead.set(email_field, email)
    if status_field:
        lead.set(status_field, captured_status)
        
    lead.insert(ignore_permissions=True)
    
    return {"status": "success", "message": _("Lead captured successfully")}
