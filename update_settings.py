import frappe
import os

def execute():
    frappe.init(site="huf-reason.localhost", sites_path="/home/muneeb/huf/sites")
    frappe.connect()
    
    settings = frappe.get_single("Ghost Settings")
    changed = False
    
    if not settings.lead_doctype:
        settings.lead_doctype = "Ghost Lead"
        changed = True
    if not settings.lead_email_fieldname:
        settings.lead_email_fieldname = "captured_email"
        changed = True
    if not settings.lead_ghost_fieldname:
        settings.lead_ghost_fieldname = "ghost_email"
        changed = True
    if not settings.lead_status_fieldname:
        settings.lead_status_fieldname = "status"
        changed = True
    if not settings.lead_captured_status:
        settings.lead_captured_status = "Captured"
        changed = True
    if not settings.lead_converted_status:
        settings.lead_converted_status = "Converted"
        changed = True
        
    if changed:
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Ghost Settings defaults in DB.")
    else:
        print("No updates needed.")
        
    frappe.destroy()

if __name__ == "__main__":
    execute()
