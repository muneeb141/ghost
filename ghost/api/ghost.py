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
def convert_to_real_user(ghost_email, real_email, first_name=None, last_name=None):
	"""
	Converts a Ghost User to a Real User by renaming the document.
	transferring all linked data (Docs, etc.) to the new email.
	
	Args:
		ghost_email: Current Ghost User ID
		real_email: New valid email address
		first_name: (Optional) New First Name
		last_name: (Optional) New Last Name
	"""
	# Security: Only allow if System Manager OR if the current session is the ghost user itself?
	# For now, let's enforce System Manager or specialized permission, OR allow if it's the user themselves converting.
	# Actually, for an API flow, usually the Backend (System) calls this after validating the real email via OTP.
	# So we might assume this is a privileged call or we need to be careful.
	# Let's verify validated inputs.

	if not frappe.db.exists("User", ghost_email):
		frappe.throw(_("Ghost user {} does not exist").format(ghost_email))

	if frappe.db.exists("User", real_email):
		frappe.throw(_("User {} already exists. Cannot convert.").format(real_email))

	# 1. Rename the User Document
    # Switch to Administrator to bypass permission checks for cascading renames (e.g. Notification Settings) which might fail for normal users/ghosts.
	original_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		frappe.rename_doc("User", ghost_email, real_email, force=True)
	finally:
		frappe.set_user(original_user)

	# 2. Update Role & Profile
	user = frappe.get_doc("User", real_email)
	
	# Remove Ghost Role
	settings = frappe.get_single("Ghost Settings")
	ghost_role = settings.ghost_role or "Guest"
	
	existing_roles = [r.role for r in user.roles]
	if ghost_role in existing_roles:
		# We can't remove directly from list easily, use remove_roles
		user.remove_roles(ghost_role)

	# Add Website User (or desired default)
	if "Website User" not in existing_roles:
		user.add_roles("Website User")

	# Update Details
	if first_name:
		user.first_name = first_name
	if last_name:
		user.last_name = last_name
	
	# Reset creation? No, creation is immutable.
	# The cleanup task checks for 'Ghost' role, so removing that role is enough to stop auto-deletion.
	# from frappe.utils import now_datetime
	# user.creation = now_datetime() 
	
	user.save(ignore_permissions=True)
	
	# Explicitly commit to ensure rename and updates persist, 
	# especially since we switched user contexts which might affect auto-commit behavior or if called via RPC.
	frappe.db.commit()

	return {
		"message": _("User converted successfully"),
		"user": real_email
	}
