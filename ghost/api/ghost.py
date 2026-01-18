import frappe
from frappe import _
from frappe.utils import random_string, get_url
import uuid

import frappe.rate_limiter

@frappe.whitelist(allow_guest=True)
@frappe.rate_limiter.rate_limit(limit=100, seconds=3600)
def create_ghost_session(email=None):
	"""
	Creates a Ghost User and returns their API Key/Secret + Session details.
	"""
	settings = frappe.get_single('Ghost Settings')
	if not settings.enable_ghost_feature:
		frappe.throw("Ghost feature is disabled.")

	ghost_role = settings.ghost_role or "Guest"
	domain = settings.ghost_email_domain or "guest.local"

	# Generate Email
	if not email:
		unique_id = str(uuid.uuid4())[:8]
		email = f"ghost_{unique_id}@{domain}"
	else:
		# If email provided, ensure it's not taken, or return existing ghost?
		# For safety, we enforce generated emails for now unless specified.
		pass

	if frappe.db.exists("User", email):
		# Re-use? Or error? For now, assume new session needed.
		pass

	# Create User
	user = frappe.new_doc("User")
	user.email = email
	user.first_name = "Ghost"
	user.last_name = "User"
	user.send_welcome_email = 0
	user.roles = []
	
	try:
		user.save(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		user = frappe.get_doc("User", email)

	# Assign Role
	if ghost_role not in [r.role for r in user.roles]:
		user.add_roles(ghost_role)

	# Generate Keys
	api_key = random_string(16)
	api_secret = random_string(16)
	
	user.api_key = api_key
	user.api_secret = api_secret
	user.save(ignore_permissions=True)

	# Login (generate session)
	# For API usage, keys are enough. But for frontend session, we might want cookies.
	# Here we return keys for API usage as requested "api calling from frontend".
	
	return {
		"user": email,
		"api_key": api_key,
		"api_secret": api_secret,
		"message": "Ghost session created"
	}

@frappe.whitelist()
def convert_to_real_user(ghost_email, real_email, first_name=None, last_name=None, otp_code=None):
	"""
	Converts a Ghost User to a Real User.
	- If Real User exists: Merges Ghost data into Real User.
	- If Real User does not exist: Renames Ghost User to Real User.
	"""
	from ghost.ghost.doctype.otp.otp import verify as verify_otp

	settings = frappe.get_single("Ghost Settings")

	if not frappe.db.exists("User", ghost_email):
		frappe.throw(_("Ghost user {} does not exist").format(ghost_email))

	# Optional: Verify OTP before conversion if enabled
	if settings.verify_otp_on_conversion:
		if not otp_code:
			frappe.throw(_("OTP Code is required for conversion."))
		
		# Verify the OTP for the REAL email (since that is what we are verifying ownership of)
		# This will raise exception if invalid or expired.
		verify_otp(otp_code, email=real_email, purpose="Conversion")

	# Check if target exists
	target_exists = frappe.db.exists("User", real_email)

	# 1. Rename / Merge
	original_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		# If target exists, merge=True. If not, merge=False (rename).
		frappe.rename_doc("User", ghost_email, real_email, force=True, merge=bool(target_exists))
	finally:
		frappe.set_user(original_user)

	# 2. Update Role & Profile (of the resulting user)
	user = frappe.get_doc("User", real_email)
	
	# Remove Ghost Role
	ghost_role = settings.ghost_role or "Guest"
	existing_roles = [r.role for r in user.roles]
	
	# If converted role is configured, use it. Otherwise default to Website User logic.
	target_role = settings.default_user_role
	
	# Transition: Remove Ghost -> Add Target
	if ghost_role in existing_roles:
		user.remove_roles(ghost_role)
		
	if target_role:
		if target_role not in existing_roles:
			user.add_roles(target_role)
	else:
		# Fallback: maintain basic access
		if "Website User" not in existing_roles:
			user.add_roles("Website User")

	# Update Details
	if first_name:
		user.first_name = first_name
	if last_name:
		user.last_name = last_name
	
	user.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"message": _("User converted/merged successfully"),
		"user": real_email,
		"merged": target_exists
	}
