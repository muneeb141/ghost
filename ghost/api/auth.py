import frappe
from frappe import _
from frappe.utils import random_string, now_datetime, add_to_date
from ghost.ghost.doctype.otp.otp import verify as ghost_verify_otp

@frappe.whitelist(allow_guest=True)
def login(otp, email=None, mobile_no=None, first_name=None, last_name=None, client_id=None):
	"""
	Centralized Authentication API.
	"""
	# Priority: 1. Backend Setting (Best Practice), 2. API Param (Override/Fallback)
	backend_client_id = frappe.db.get_single_value("Ghost Settings", "client_id")
	if backend_client_id:
		client_id = backend_client_id

	
	if not email and not mobile_no:
		frappe.throw(_("Please provide either Email or Mobile Number"))

	# 1. Identify Context (Ghost vs Guest)
	current_user = frappe.session.user
	is_ghost = current_user.startswith("ghost_")
	
	user_to_login = None
	
	try:
		if is_ghost:
			# --- Scenario A: Ghost Conversion ---
			from ghost.api.ghost import convert_to_real_user
			
			target_email = email or f"{mobile_no}@mobile.login"
			
			# Ghost App handles the merge/rename logic
			# This will raise exception if OTP is invalid (if strictly enforced)
			result = convert_to_real_user(
				ghost_email=current_user, 
				real_email=target_email, 
				first_name=first_name, 
				last_name=last_name, 
				otp_code=otp
			)
			
			# If successful, the user is now the target email
			user_to_login = target_email
			
		else:
			# --- Scenario B: Direct Login / Signup ---
			
			# 1. Verify OTP (Stateless verification)
			ghost_verify_otp(otp_code=otp, email=email, phone=mobile_no, purpose="Login")
			
			# 2. Find or Create User
			if email:
				user_to_login = frappe.db.get_value("User", {"email": email}, "name")
				if not user_to_login:
					# Create New User (Direct Signup)
					user_to_login = create_new_user(email=email, first_name=first_name or email.split("@")[0], last_name=last_name)
			elif mobile_no:
				user_to_login = frappe.db.get_value("User", {"mobile_no": mobile_no}, "name")
				if not user_to_login:
					placeholder = f"{mobile_no}@mobile.login"
					user_to_login = create_new_user(email=placeholder, mobile_no=mobile_no, first_name=first_name or mobile_no, last_name=last_name)

		# 3. Perform Login
		if user_to_login:
			# A. Session Login (Cookies)
			# Only attempt if we have a request object (Web Context)
			if getattr(frappe.local, "request", None):
				from frappe.auth import LoginManager
				frappe.local.login_manager = LoginManager()
				frappe.local.login_manager.login_as(user_to_login)
			
			response = {
				"status": "success",
				"message": "Logged In",
				"user": user_to_login
			}

			# B. OAuth Token (API Support)
			if client_id:
				tokens = generate_oauth_tokens(user_to_login, client_id)
				if tokens:
					response.update(tokens)
			
			return response
			
		else:
			frappe.throw(_("User could not be determined after verification"))

	except Exception as e:
		frappe.log_error(f"Ghost Login Failed: {str(e)}")
		frappe.throw(_("Authentication Failed: ") + str(e))


def create_new_user(email, mobile_no=None, first_name="Customer", last_name=None):
	"""
	Helper to create a new user with the default role from settings.
	"""
	settings = frappe.get_single("Ghost Settings")
	default_role = settings.default_user_role or "Customer"

	user = frappe.new_doc("User")
	user.email = email
	user.first_name = first_name
	user.last_name = last_name
	user.mobile_no = mobile_no
	user.enabled = 1
	
	if default_role:
		user.append("roles", {
			"doctype": "Has Role",
			"role": default_role
		})
		
	user.insert(ignore_permissions=True)
	return user.name

def generate_oauth_tokens(user, client_id=None):
	"""
	Creates OAuth Bearer Tokens with configurable expiration from Ghost Settings.
	Returns access_token, refresh_token, expires_in, and token_type.
	"""
	settings = frappe.get_single("Ghost Settings")
	
	# Use client_id from settings if not provided
	if not client_id:
		client_id = settings.client_id
	
	if not client_id:
		frappe.throw(_("OAuth Client ID is not configured in Ghost Settings"))
	
	# Verify client exists
	if not frappe.db.exists("OAuth Client", client_id):
		frappe.throw(_("OAuth Client {0} does not exist").format(client_id))
	
	# Get token configuration from settings
	access_expiry_seconds = int(settings.access_token_expiry_seconds or 3600)  # Default: 1 hour
	refresh_expiry_days = int(settings.refresh_token_expiry_days or 30)  # Default: 30 days
	scopes = settings.ghost_token_scope or "all"
	
	# Create OAuth Bearer Token
	bearer_token = frappe.new_doc("OAuth Bearer Token")
	bearer_token.client = client_id
	bearer_token.user = user
	bearer_token.scopes = scopes
	bearer_token.status = "Active"
	bearer_token.expires_in = access_expiry_seconds
	bearer_token.expiration_time = add_to_date(now_datetime(), seconds=access_expiry_seconds)
	
	# Generate secure random tokens
	bearer_token.access_token = frappe.generate_hash(length=30)
	bearer_token.refresh_token = frappe.generate_hash(length=30)
	
	# Store refresh token expiration in a custom field or calculate on refresh
	# For now, we'll handle expiration in the refresh endpoint
	
	bearer_token.insert(ignore_permissions=True)
	frappe.db.commit()
	
	frappe.logger().info(f"Generated OAuth tokens for user: {user}")
	
	return {
		"access_token": bearer_token.access_token,
		"refresh_token": bearer_token.refresh_token,
		"expires_in": access_expiry_seconds,
		"token_type": "Bearer"
	}

@frappe.whitelist(allow_guest=True)
def refresh_bearer_token(refresh_token):
	"""
	Refreshes an expired access token using a valid refresh token.
	Returns new access_token and optionally rotates refresh_token.
	"""
	if not refresh_token:
		frappe.throw(_("Refresh token is required"))
	
	# Find the bearer token by refresh_token
	token_name = frappe.db.get_value(
		"OAuth Bearer Token",
		{"refresh_token": refresh_token, "status": "Active"},
		["name", "user", "client", "creation"],
		as_dict=True
	)
	
	if not token_name:
		frappe.throw(_("Invalid or expired refresh token"), frappe.AuthenticationError)
	
	# Check if refresh token has expired (based on creation date + expiry days)
	settings = frappe.get_single("Ghost Settings")
	refresh_expiry_days = int(settings.refresh_token_expiry_days or 30)
	
	token_age = now_datetime() - token_name.creation
	if token_age.days > refresh_expiry_days:
		# Invalidate the old token
		frappe.db.set_value("OAuth Bearer Token", token_name.name, "status", "Revoked")
		frappe.db.commit()
		frappe.throw(_("Refresh token has expired. Please login again."), frappe.AuthenticationError)
	
	# Revoke the old token
	frappe.db.set_value("OAuth Bearer Token", token_name.name, "status", "Revoked")
	frappe.db.commit()
	
	# Generate new tokens for the same user and client
	new_tokens = generate_oauth_tokens(token_name.user, token_name.client)
	
	frappe.logger().info(f"Refreshed OAuth tokens for user: {token_name.user}")
	
	return {
		"status": "success",
		"message": "Token refreshed successfully",
		"user": token_name.user,
		**new_tokens
	}


def _google_client_id():
	"""Return the configured Google OAuth web client id, or raise."""
	client_id = frappe.conf.get("google_web_client_id")
	if not client_id:
		frappe.throw(
			_("Google login is not configured. Set 'google_web_client_id' in site config.")
		)
	return client_id


def _verify_google_id_token(token):
	"""Verify a Google ID token's signature, audience and expiry; return its claims.

	Isolated so the single crypto/network call has one home and can be mocked in
	tests. Uses Google's own library (google-auth) — we never parse the JWT
	ourselves. The audience is pinned to our client id, which is what stops a
	token minted for another app from being replayed against us.
	"""
	from google.auth.transport.requests import Request
	from google.oauth2 import id_token as google_id_token

	try:
		return google_id_token.verify_oauth2_token(token, Request(), audience=_google_client_id())
	except ValueError:
		# google-auth raises ValueError on bad signature, wrong audience or expiry.
		frappe.throw(_("Invalid Google token"), frappe.AuthenticationError)


@frappe.whitelist(allow_guest=True)
def google_login(id_token, client_id=None):
	"""Authenticate with a Google ID token from the native Sign-In SDK.

	The email is verified by Google upfront, so there is no ghost/placeholder
	stage: find the user by email, else create one via the shared
	create_new_user (which applies the default role from Ghost Settings), then
	mint the usual OAuth tokens. Returns the same token shape as OTP login.
	"""
	if not id_token:
		frappe.throw(_("Google ID token is required"))

	info = _verify_google_id_token(id_token)

	if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
		frappe.throw(_("Invalid Google token issuer"), frappe.AuthenticationError)

	if not info.get("email_verified"):
		frappe.throw(_("Google account email is not verified"), frappe.AuthenticationError)

	email = info.get("email")
	if not email:
		frappe.throw(_("Google account has no email"), frappe.AuthenticationError)

	existing = frappe.db.get_value("User", {"email": email}, "name")
	user = existing or create_new_user(
		email=email,
		first_name=info.get("given_name") or email.split("@")[0],
		last_name=info.get("family_name"),
	)

	response = {
		"status": "success",
		"user": user,
		"is_new_user": not existing,
	}

	tokens = generate_oauth_tokens(user, client_id)
	if tokens:
		response.update(tokens)

	return response
