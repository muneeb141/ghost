import frappe
from ghost.api.lead import capture_email
from ghost.api.ghost import create_ghost_session, convert_to_real_user

def debug():
    frappe.init(site="huf-reason.localhost")
    frappe.connect()
    
    frappe.db.sql("DELETE FROM `tabUser` WHERE email IN ('lead_debug_ghost@guest.local', 'lead_debug_real@example.com')")
    frappe.db.sql("DELETE FROM `tabGhost Lead`")
    frappe.db.commit()
    
    settings = frappe.get_single("Ghost Settings")
    settings.enable_ghost_feature = 1
    settings.enable_lead_capture = 1
    settings.verify_otp_on_conversion = 0
    settings.save()
    
    # 1. Create ghost user
    session = create_ghost_session("lead_debug_ghost@guest.local")
    ghost_email = session["user"]
    print(f"Ghost email: {ghost_email}")
    
    # 2. Capture lead
    capture_email(ghost_email, "lead_debug_real@example.com")
    
    # Check lead before
    print("Before conversion:")
    print(frappe.db.get_all("Ghost Lead", fields=["name", "ghost_email", "captured_email", "status"]))
    
    # 3. Convert
    convert_to_real_user(ghost_email, "lead_debug_real@example.com")
    
    # Check lead after
    print("After conversion:")
    print(frappe.db.get_all("Ghost Lead", fields=["name", "ghost_email", "captured_email", "status"]))

if __name__ == "__main__":
    debug()
