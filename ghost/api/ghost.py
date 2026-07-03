import frappe
from frappe import _
from frappe.utils import random_string, get_url
from frappe.utils.password import rename_password
import uuid
import time

import frappe.rate_limiter

# Tables that a ghost user (fresh login, no history) will actually have rows in.
# rename_doc scans all 42+ User link tables; this targeted list skips the empty ones
# on large production tables and avoids the timeout.
_GHOST_LINK_TABLES = [
	("OAuth Bearer Token", "user"),
	("OAuth Authorization Code", "user"),
	("Token Cache", "user"),
	("Route History", "user"),
	("Activity Log", "user"),
	# Activity Log rows the ghost created carry the ghost email in owner/modified_by;
	# rewrite them so the activity feed shows the converted user, not the ghost.
	("Activity Log", "owner"),
	("Activity Log", "modified_by"),
	# Contact created during the ghost flow is owned by the ghost; reassign to the
	# converted user so the record's creator is the real account.
	("Contact", "owner"),
	("Contact", "modified_by"),
	("Notification Settings", "user"),
	("Notification Log", "for_user"),
	("Notification Log", "from_user"),
]

_GHOST_CHILD_TABLES = [
	"Has Role",
	"User Role Profile",
	"User Email",
	"Block Module",
	"DefaultValue",
	"User Social Login",
]

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
	Converts a Ghost User to a Real User using one of two conversion modes:
	- rename: lightweight rename when target user does not exist
	- manual_migration: app-level migration when target user already exists
	"""
	from ghost.ghost.doctype.otp.otp import verify as verify_otp
	from ghost.api.auth import generate_oauth_tokens

	total_start = time.monotonic()
	logger = frappe.logger("ghost_conversion")
	settings = frappe.get_single("Ghost Settings")

	# Prefer authenticated session user when it is a ghost user and differs
	# from a stale client-supplied ghost_email
	current_user = frappe.session.user
	if current_user.startswith("ghost_") and current_user != ghost_email:
		ghost_email = current_user

	if not frappe.db.exists("User", ghost_email):
		# The ghost may have already been renamed on a previous request that timed out on the
		# client side. After rename_doc completes, the caller's OAuth token is re-associated
		# with real_email, so frappe.session.user will equal real_email on retry.
		if frappe.session.user == real_email and frappe.db.exists("User", real_email):
			try:
				retry_tokens = generate_oauth_tokens(real_email)
			except Exception as e:
				frappe.log_error(f"Failed to generate tokens on idempotent retry for {real_email}: {str(e)}")
				retry_tokens = None
			retry_response = {
				"message": _("User converted successfully"),
				"user": real_email,
				"merged": False,
				"conversion_mode": "already_converted",
			}
			if retry_tokens:
				retry_response.update({
					"access_token": retry_tokens["access_token"],
					"refresh_token": retry_tokens["refresh_token"],
					"expires_in": retry_tokens["expires_in"],
					"token_type": retry_tokens["token_type"],
				})
			return retry_response
		frappe.throw(_("Ghost user {} does not exist").format(ghost_email))

	otp_start = time.monotonic()
	if settings.verify_otp_on_conversion:
		if not otp_code:
			frappe.throw(_("OTP Code is required for conversion."))

		verify_otp(otp_code, email=real_email, purpose="Conversion")
	logger.info(
		f"Ghost conversion OTP verification duration_ms={(time.monotonic() - otp_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email}"
	)

	# Capture the source user's mobile before rename/migrate renames or disables it,
	# so it can be carried onto the converted user below (Phone Lookup / mobile login
	# find returning users by User.mobile_no).
	ghost_mobile = frappe.db.get_value("User", ghost_email, "mobile_no")

	existence_start = time.monotonic()
	target_exists = frappe.db.exists("User", real_email)
	logger.info(
		f"Ghost conversion target existence check duration_ms={(time.monotonic() - existence_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email} target_exists={bool(target_exists)}"
	)

	original_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		branch_start = time.monotonic()
		if target_exists:
			migration_stats = migrate_ghost_data_to_existing_user(ghost_email, real_email)
			conversion_mode = "manual_migration"
			merged = False
		else:
			convert_by_rename(ghost_email, real_email)
			migration_stats = {}
			conversion_mode = "rename"
			merged = False
			# The ghost user no longer exists after the rename, so restore the session
			# to the real user instead of the dead ghost. This matters because the
			# user.save() below triggers core User.on_update, which enqueues
			# create_contact with enqueue_after_commit=True. frappe.enqueue captures
			# frappe.session.user (background_jobs.py) and the worker runs the job as
			# that user (frappe.set_user in execute_job), so the Contact — and any
			# other post-commit doc created by user.save() — is owned by whoever the
			# session is here. Without this, the new Contact would be owned by the
			# ghost. (Activity Log owner is already handled synchronously in
			# convert_by_rename, since those rows exist before the rename.)
			original_user = real_email
		logger.info(
			f"Ghost conversion branch duration_ms={(time.monotonic() - branch_start) * 1000:.2f} "
			f"ghost={ghost_email} real={real_email} mode={conversion_mode}"
		)
	finally:
		frappe.set_user(original_user)

	role_profile_start = time.monotonic()
	user = frappe.get_doc("User", real_email)
	apply_user_profile_and_roles(
		user=user,
		settings=settings,
		first_name=first_name,
		last_name=last_name,
		conservative_name_update=target_exists,
	)
	# Carry the phone forward so future mobile logins recognize this user, and so
	# the linked Contact gets the number too. mobile_no is UNIQUE: the merge path
	# leaves the number on the now-disabled source user, which would collide —
	# release it there first, then set it on the target and let save() persist it
	# and sync the Contact (User.on_update -> create_contact). The rename path
	# already carries the number on the same row, so the guard skips it.
	if ghost_mobile and not user.mobile_no:
		if ghost_email != real_email and frappe.db.exists("User", ghost_email):
			frappe.db.set_value("User", ghost_email, "mobile_no", None, update_modified=False)
		user.mobile_no = ghost_mobile

	user.save(ignore_permissions=True)
	logger.info(
		f"Ghost conversion role/profile update duration_ms={(time.monotonic() - role_profile_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email} mode={conversion_mode}"
	)

	token_invalidation_start = time.monotonic()
	if settings.invalidate_ghost_tokens_on_conversion:
		frappe.db.sql(
			"""
			UPDATE `tabOAuth Bearer Token`
			SET status = 'Revoked'
			WHERE user = %s AND status = 'Active'
		""",
			(ghost_email,),
		)
		logger.info(f"Invalidated ghost tokens for {ghost_email}")
	logger.info(
		f"Ghost conversion token invalidation duration_ms={(time.monotonic() - token_invalidation_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email}"
	)

	token_generation_start = time.monotonic()
	try:
		new_tokens = generate_oauth_tokens(real_email)
	except Exception as e:
		frappe.log_error(f"Failed to generate tokens for converted user {real_email}: {str(e)}")
		new_tokens = None
	logger.info(
		f"Ghost conversion token generation duration_ms={(time.monotonic() - token_generation_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email}"
	)

	response = {
		"message": _("User converted successfully"),
		"user": real_email,
		"merged": merged,
		"conversion_mode": conversion_mode,
	}

	if migration_stats:
		response["migration"] = migration_stats

	if new_tokens:
		response.update({
			"access_token": new_tokens["access_token"],
			"refresh_token": new_tokens["refresh_token"],
			"expires_in": new_tokens["expires_in"],
			"token_type": new_tokens["token_type"]
		})

	frappe.db.commit()
	logger.info(
		f"Ghost conversion total duration_ms={(time.monotonic() - total_start) * 1000:.2f} "
		f"ghost={ghost_email} real={real_email} mode={conversion_mode}"
	)
	return response


def convert_by_rename(ghost_email, real_email):
	"""Fast targeted rename for ghost→new-user conversion.

	frappe.rename_doc("User") fires UPDATE queries against 42+ tables regardless of
	whether the ghost user has any rows there.  On production this causes timeouts.
	Ghost users only ever accumulate data in a small, known set of tables, so we
	update only those and skip the rest entirely.
	"""
	frappe.db.commit()

	# 1. Rename the User document itself (sets name + email column).
	frappe.db.sql(
		"UPDATE `tabUser` SET `name` = %s, `email` = %s WHERE `name` = %s",
		(real_email, real_email, ghost_email),
	)

	# 2. Child tables — parent field references the user name.
	for child_dt in _GHOST_CHILD_TABLES:
		try:
			frappe.db.sql(
				f"UPDATE `tab{child_dt}` SET `parent` = %s"
				f" WHERE `parent` = %s AND `parenttype` = 'User'",
				(real_email, ghost_email),
			)
		except Exception:
			pass

	# 3. Link tables the ghost user may have populated.
	for dt, field in _GHOST_LINK_TABLES:
		try:
			frappe.db.sql(
				f"UPDATE `tab{dt}` SET `{field}` = %s WHERE `{field}` = %s",
				(real_email, ghost_email),
			)
		except Exception:
			pass

	# 4. Transfer the password hash row (no-op for ghost users but safe to call).
	try:
		rename_password("User", ghost_email, real_email)
	except Exception:
		pass

	frappe.db.commit()
	frappe.clear_cache()


def get_ghost_owned_reassignment_plan():
	"""
	Only includes app-owned doctypes and safe, explicit field updates.
	"""
	return [
		{
			"doctype": "OTP",
			"field": "user",
			"description": "Reassign OTP user reference from ghost to real user",
		},
		{
			"doctype": "OTP",
			"field": "email",
			"description": "Reassign OTP email when it matches ghost email",
		},
	]


def migrate_ghost_data_to_existing_user(ghost_email, real_email):
	migration_counts = {}
	for rule in get_ghost_owned_reassignment_plan():
		count = frappe.db.count(rule["doctype"], filters={rule["field"]: ghost_email})
		if count:
			frappe.db.sql(
				f"UPDATE `tab{rule['doctype']}` SET `{rule['field']}` = %s WHERE `{rule['field']}` = %s",
				(real_email, ghost_email),
			)
		migration_counts[f"{rule['doctype']}.{rule['field']}"] = count

	# Keep ghost user for audit/history; disable it so it cannot be used after migration.
	frappe.db.set_value("User", ghost_email, "enabled", 0, update_modified=False)
	return migration_counts


def apply_user_profile_and_roles(user, settings, first_name=None, last_name=None, conservative_name_update=False):
	ghost_role = settings.ghost_role or "Ghost"
	target_role = settings.default_user_role or "Website User"
	new_roles = [r for r in user.roles if r.role != ghost_role]
	existing_role_names = [r.role for r in new_roles]

	if target_role and target_role not in existing_role_names:
		if frappe.db.exists("Role", target_role):
			new_roles.append({"doctype": "Has Role", "role": target_role})
		else:
			frappe.log_error(f"Role '{target_role}' not found, skipping role assignment during conversion")

	if not new_roles:
		for fallback_role in ["Website User", "Guest", "All"]:
			if frappe.db.exists("Role", fallback_role):
				new_roles.append({"doctype": "Has Role", "role": fallback_role})
				break
	user.set("roles", new_roles)

	if first_name and (not conservative_name_update or not user.first_name):
		user.first_name = first_name
	if last_name and (not conservative_name_update or not user.last_name):
		user.last_name = last_name
