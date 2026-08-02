import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def capture_email(ghost_email, email):
    """
    Capture a ghost user's email before full conversion.
    Allows for abandoned session recovery.
    """
    settings = frappe.get_single("Ghost Settings")
    if not settings.enable_lead_capture:
        frappe.throw(_("Lead Capture is not enabled"), frappe.PermissionError)
        
    if not ghost_email or not email:
        frappe.throw(_("Both ghost_email and email are required"))
        
    if not frappe.db.exists("User", ghost_email):
        frappe.throw(_("Invalid Ghost User"))
        
    # Check if this ghost user already captured an email
    existing_lead = frappe.db.get_value("Ghost Lead", {"ghost_email": ghost_email}, "name")
    if existing_lead:
        # Update the captured email if it changed
        frappe.db.set_value("Ghost Lead", existing_lead, "captured_email", email)
        return {"status": "success", "message": _("Lead updated successfully")}
        
    # Create new lead
    lead = frappe.get_doc({
        "doctype": "Ghost Lead",
        "ghost_email": ghost_email,
        "captured_email": email,
        "status": "Captured"
    })
    lead.insert(ignore_permissions=True)
    
    return {"status": "success", "message": _("Lead captured successfully")}
