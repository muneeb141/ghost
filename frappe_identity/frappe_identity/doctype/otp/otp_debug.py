import frappe
def test_settings_config():
    s = frappe.get_single("OTP Settings")
    print(f"Delivery: {s.otp_delivery_type}")
    print(f"Email Account: {s.email_account}")
    print(f"SMS Sender: {s.sms_sender}")
