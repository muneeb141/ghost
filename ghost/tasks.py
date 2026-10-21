import re
from functools import partial

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime


def delete_expired_ghost_users():
	"""Expire only server-shaped anonymous Website Users through native deletion.

	Linked users are disabled and retained; never force-delete business references.
	The job wrapper owns the transaction. Each candidate has its own rollback savepoint.
	"""
	settings = frappe.get_single("Ghost Settings")
	if not settings.enable_ghost_feature or not settings.enable_auto_cleanup:
		return
	# Native User deletion may log out through a request LoginManager and commit.
	# This scheduled task must run without an interactive request context.
	if getattr(frappe.local, "login_manager", None):
		frappe.throw(_("Ghost cleanup must run in a background job or CLI context"))
	role = settings.ghost_role or "Ghost"
	if frappe.db.get_value("Role", role, "desk_access"):
		return
	expiration_days = max(1, int(settings.expiration_days or 30))
	batch_size = min(100, max(1, int(settings.cleanup_batch_size or 100)))
	domain = (settings.ghost_email_domain or "guest.local").lower()
	pattern = rf"ghost_(?:[0-9a-f]{{8}}|[0-9a-f]{{32}})@{re.escape(domain)}"
	cutoff = add_days(now_datetime(), -expiration_days)
	users = frappe.get_all(
		"User",
		filters=[
			["User", "creation", "<", cutoff],
			["User", "user_type", "=", "Website User"],
			["User", "enabled", "=", 1],
			["User", "name", "like", f"ghost_%@{domain}"],
			["Has Role", "role", "=", role],
		],
		pluck="name",
		order_by="`tabUser`.`creation` asc",
		limit=batch_size,
	)
	for name in users:
		if not re.fullmatch(pattern, name) or role not in frappe.get_roles(name):
			continue
		frappe.db.savepoint("ghost_cleanup_user")
		try:
			# Serialize against a verified conversion and recheck after acquiring the lock.
			user = frappe.db.get_value(
				"User", name, ["name", "enabled", "user_type", "creation"], as_dict=True, for_update=True
			)
			if (
				not user
				or not user.enabled
				or user.user_type != "Website User"
				or get_datetime(user.creation) >= get_datetime(cutoff)
				or role not in frappe.get_roles(name)
			):
				continue
			for token in frappe.get_all("OAuth Bearer Token", filters={"user": name}, pluck="name"):
				frappe.delete_doc("OAuth Bearer Token", token, ignore_permissions=True)
			frappe.delete_doc("User", name, ignore_permissions=True)
		except frappe.LinkExistsError:
			frappe.db.rollback(save_point="ghost_cleanup_user")
			# Expire credentials but preserve linked leads, bookings and other native references.
			frappe.db.set_value("User", name, "enabled", 0, update_modified=False)
			frappe.db.set_value(
				"OAuth Bearer Token", {"user": name}, "status", "Revoked", update_modified=False
			)
			# Native session deletion commits. Run only after the job transaction succeeds.
			frappe.db.after_commit.add(partial(_clear_expired_sessions, name))
			frappe.clear_cache(user=name)
			frappe.logger("ghost_cleanup").info(
				"Retained linked expired Ghost user %s; credentials disabled", name
			)
		except Exception:
			frappe.db.rollback(save_point="ghost_cleanup_user")
			frappe.log_error(title="Ghost cleanup failed", message=frappe.get_traceback())


def _clear_expired_sessions(user):
	"""After-commit cleanup; a savepoint rollback may have restored an enabled user."""
	if frappe.db.get_value("User", user, "enabled"):
		return
	from frappe.sessions import clear_sessions

	clear_sessions(user=user, force=True)


def expire_otps():
	"""
	Scheduled function to expire OTPs that have passed their expiry time
	This should be run periodically (e.g., every 5-10 minutes)
	"""
	try:
		expired_otps = frappe.get_all(
			"Ghost OTP", filters={"status": "Valid", "expiry": ["<", now_datetime()]}, fields=["name"]
		)

		count = 0
		for otp in expired_otps:
			try:
				otp_doc = frappe.get_doc("Ghost OTP", otp.name)
				otp_doc.status = "Expired"
				otp_doc.save(ignore_permissions=True)
				count += 1
			except Exception as e:
				frappe.log_error(f"Error expiring OTP {otp.name}: {e}", "OTP Expiration")

		return {"expired_count": count}
	except Exception as e:
		frappe.log_error(f"Error in expire_otps scheduled function: {e}", "OTP Expiration")
		return {"expired_count": 0, "error": e}


def send_lead_reminders():
	"""
	Find leads older than lead_reminder_hours that haven't converted,
	send a reminder email, and mark conversion_reminder_sent.
	"""
	settings = frappe.get_single("Ghost Settings")
	if not settings.enable_lead_capture or not settings.lead_reminder_email_template:
		return

	reminder_hours = settings.lead_reminder_hours or 24
	from frappe.utils import add_to_date

	threshold_date = add_to_date(now_datetime(), hours=-reminder_hours)

	leads = frappe.get_all(
		"Ghost Lead",
		filters={"status": "Captured", "conversion_reminder_sent": 0, "creation": ["<", threshold_date]},
		fields=["name", "ghost_email", "captured_email"],
	)

	if not leads:
		return

	email_template = frappe.get_doc("Email Template", settings.lead_reminder_email_template)

	for lead in leads:
		try:
			args = {"ghost_email": lead.ghost_email, "captured_email": lead.captured_email}
			subject = email_template.get_formatted_subject(args)
			content = email_template.get_formatted_response(args)

			frappe.sendmail(recipients=[lead.captured_email], subject=subject, content=content, now=True)

			frappe.db.set_value("Ghost Lead", lead.name, "conversion_reminder_sent", 1)
		except Exception as e:
			frappe.log_error(f"Error sending lead reminder to {lead.captured_email}: {e!s}", "Lead Reminder")


def delete_old_conversion_logs():
	"""
	Deletes Ghost Conversion Log entries older than the configured retention.
	Skips silently when conversion logging is disabled.
	"""
	settings = frappe.get_single("Ghost Settings")
	if not getattr(settings, "enable_conversion_logging", 0):
		return

	retention_days = settings.conversion_log_retention_days or 90
	if retention_days < 1:
		retention_days = 1

	cutoff = add_days(now_datetime(), -retention_days)
	frappe.db.delete("Ghost Conversion Log", {"converted_at": ["<", cutoff]})
