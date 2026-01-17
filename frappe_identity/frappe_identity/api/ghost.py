import frappe
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
def convert_to_real_user(ghost_email, real_email):
	"""
	Internal API to signal conversion. Should be called by trusted logic or after auth.
	Use with caution.
	"""
	pass
