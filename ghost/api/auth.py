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
			# We use "Conversion" purpose for now as it shares the same flow intent (High security)
			# or we could make this "Login" if we update OTP doctype options.
			ghost_verify_otp(otp_code=otp, email=email, phone=mobile_no, purpose="Conversion")
			
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
				"user": user_to_login,
				"key_details": get_api_keys(user_to_login)
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

def generate_oauth_tokens(user, client_id):
	"""
	Manually creates a valid OAuth Bearer Token document in Frappe.
	"""
	try:
		scopes = "all" 
		expires_in = 36000 
		
		bearer_token = frappe.new_doc("OAuth Bearer Token")
		bearer_token.client = client_id
		bearer_token.user = user
		bearer_token.scopes = scopes
		bearer_token.status = "Active"
		bearer_token.expires_in = expires_in
		bearer_token.expiration_time = add_to_date(now_datetime(), seconds=expires_in)
		
		bearer_token.access_token = random_string(30) 
		bearer_token.refresh_token = random_string(30)
		
		bearer_token.save(ignore_permissions=True)
		frappe.db.commit()
		
		return {
			"access_token": bearer_token.access_token,
			"refresh_token": bearer_token.refresh_token
		}
	except Exception as e:
		frappe.log_error(f"Generate Token Failed for {user}: {str(e)}")
		return None

def get_api_keys(user):
	return {}
