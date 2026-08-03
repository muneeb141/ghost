import frappe
from frappe import _

def find_related_ghosts(real_email):
    """
    Finds all ghost sessions related to the target email.
    """
    ghosts = set()
    settings = frappe.get_single("Ghost Settings")
    
    if settings.merge_detection_method in ("Lead Email", "Both"):
        lead_dt = settings.lead_doctype or "Ghost Lead"
        email_field = settings.lead_email_fieldname or "captured_email"
        ghost_field = settings.lead_ghost_fieldname or "ghost_email"
        
        if frappe.db.exists("DocType", lead_dt):
            try:
                leads = frappe.get_all(lead_dt, 
                                       filters={email_field: real_email}, 
                                       fields=[ghost_field])
                for lead in leads:
                    ghosts.add(lead.get(ghost_field))
            except Exception as e:
                frappe.log_error(f"Failed to find related ghosts via Lead Email: {e}", "Ghost Merge")
                
    if settings.merge_detection_method in ("Fingerprint", "Both"):
        if frappe.db.exists("DocType", "Ghost Session Fingerprint"):
            # Future implementation for Phase 3 (Feature 9)
            pass
            
    return list(ghosts)


def merge_all_ghosts(ghost_emails, real_email):
    """
    Merges a list of ghost emails into the real email by running migrate_ghost_data_to_existing_user.
    """
    from ghost.api.ghost import migrate_ghost_data_to_existing_user
    
    merged_count = 0
    for ghost_email in ghost_emails:
        if ghost_email == real_email:
            continue
            
        # Ensure it's actually a ghost user before migrating
        if not frappe.db.exists("User", ghost_email):
            continue
            
        ghost_role = frappe.get_single("Ghost Settings").ghost_role
        if ghost_role not in frappe.get_roles(ghost_email):
            continue
            
        try:
            migrate_ghost_data_to_existing_user(ghost_email, real_email)
            # After migrating, we should delete the ghost user since they are merged
            frappe.delete_doc("User", ghost_email, ignore_permissions=True, force=1)
            merged_count += 1
        except Exception as e:
            frappe.log_error(f"Failed to merge {ghost_email} into {real_email}: {e}", "Ghost Merge")
            
    return merged_count
