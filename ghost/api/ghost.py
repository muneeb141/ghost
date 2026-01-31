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
		user.save(ignore_permissions=True)

	# Generate OAuth Bearer Tokens instead of API keys
	from ghost.api.auth import generate_oauth_tokens
	
	try:
		tokens = generate_oauth_tokens(user.name)
	except Exception as e:
		frappe.log_error(f"Failed to generate tokens for ghost user {user.name}: {str(e)}")
		frappe.throw(_("Failed to generate authentication tokens. Please check Ghost Settings."))
	
	return {
		"user": email,
		"access_token": tokens["access_token"],
		"refresh_token": tokens["refresh_token"],
		"expires_in": tokens["expires_in"],
		"token_type": tokens["token_type"],
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
	# Reload to be safe after rename
	user = frappe.get_doc("User", real_email)
	
	# Transition Logic
	ghost_role = settings.ghost_role or "Ghost"
	target_role = settings.default_user_role or "Website User"

	# Filter out Ghost Role
	new_roles = [r for r in user.roles if r.role != ghost_role]
	
	# Add Target Role if not present
	existing_role_names = [r.role for r in new_roles]
	if target_role and target_role not in existing_role_names:
		new_roles.append({"doctype": "Has Role", "role": target_role})
	
	# Fallback safety (ensure at least one role)
	if not new_roles:
		new_roles.append({"doctype": "Has Role", "role": "Website User"})

	user.set("roles", new_roles)

	# Update Details
	if first_name:
		user.first_name = first_name
	if last_name:
		user.last_name = last_name
	
	user.save(ignore_permissions=True)
	frappe.db.commit()

	# 3. Token Management: Invalidate ghost tokens and generate new tokens for real user
	from ghost.api.auth import generate_oauth_tokens
	
	# Invalidate old ghost user tokens if configured
	if settings.invalidate_ghost_tokens_on_conversion:
		frappe.db.sql("""
			UPDATE `tabOAuth Bearer Token`
			SET status = 'Revoked'
			WHERE user = %s AND status = 'Active'
		""", (ghost_email,))
		frappe.db.commit()
		frappe.logger().info(f"Invalidated ghost tokens for {ghost_email}")
	
	# Generate new tokens for the converted/merged real user
	try:
		new_tokens = generate_oauth_tokens(real_email)
	except Exception as e:
		frappe.log_error(f"Failed to generate tokens for converted user {real_email}: {str(e)}")
		# Don't fail the conversion if token generation fails, just log it
		new_tokens = None

	response = {
		"message": _("User converted/merged successfully"),
		"user": real_email,
		"merged": target_exists
	}
	
	# Add new tokens to response if generated successfully
	if new_tokens:
		response.update({
			"access_token": new_tokens["access_token"],
			"refresh_token": new_tokens["refresh_token"],
			"expires_in": new_tokens["expires_in"],
			"token_type": new_tokens["token_type"]
		})
	
	return response
