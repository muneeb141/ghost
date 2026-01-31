"""
Data migration to set default values for Ghost Settings OAuth configuration.
This ensures existing installations get proper defaults.
"""

import frappe

def execute():
	"""Set default OAuth values in Ghost Settings if not already set"""
	if not frappe.db.exists("DocType", "Ghost Settings"):
		return
	
	# Get Ghost Settings
	settings = frappe.get_single("Ghost Settings")
	
	# Track if we made any changes
	modified = False
	
	# Set OAuth token defaults
	if not settings.access_token_expiry_seconds:
		settings.access_token_expiry_seconds = 3600  # 1 hour
		modified = True
	
	if not settings.refresh_token_expiry_days:
		settings.refresh_token_expiry_days = 30  # 30 days
		modified = True
	
	if not settings.ghost_token_scope:
		settings.ghost_token_scope = "all"
		modified = True
	
	if settings.invalidate_ghost_tokens_on_conversion is None:
		settings.invalidate_ghost_tokens_on_conversion = 1
		modified = True
	
	# Set OTP defaults
	if not settings.expiry_time_minutes:
		settings.expiry_time_minutes = 10
		modified = True
	
	if not settings.max_otp_attempts:
		settings.max_otp_attempts = 5
		modified = True
	
	if not settings.otp_length:
		settings.otp_length = 6
		modified = True
	
	if not settings.otp_code_type:
		settings.otp_code_type = "Numeric"
		modified = True
	
	if not settings.otp_delivery_type:
		settings.otp_delivery_type = "Email"
		modified = True
	
	# Set Ghost defaults
	if not settings.ghost_email_domain:
		settings.ghost_email_domain = "guest.local"
		modified = True
	
	if not settings.expiration_days:
		settings.expiration_days = 30
		modified = True
	
	# Save if modified
	if modified:
		settings.flags.ignore_validate = False  # We want validation to run
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		print("✅ Ghost Settings defaults initialized successfully")
	else:
		print("ℹ️  Ghost Settings already has defaults configured")
