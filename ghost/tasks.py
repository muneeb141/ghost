import frappe
from frappe.utils import add_days, now_datetime

def delete_expired_ghost_users():
	"""
	Deletes Ghost users that have exceeded the expiration days.
	Optimized to use bulk SQL deletions for high performance.
	"""
	settings = frappe.get_single("Ghost Settings")
	if not settings.enable_ghost_feature or not settings.enable_auto_cleanup:
		return

	expiration_days = settings.expiration_days or 30
	# Safety check: Don't allow very short expiration by mistake, unless 0 (immediate? No, 0 usually means disable or massive bug risk).
	if expiration_days < 1:
		expiration_days = 1
		
	batch_size = getattr(settings, "cleanup_batch_size", 500)

	expiry_date = add_days(now_datetime(), -expiration_days)
	ghost_domain = settings.ghost_email_domain or "guest.local"

	# Find users to delete
	users = frappe.db.sql("""
		SELECT name FROM `tabUser`
		WHERE creation < %s
		AND email LIKE %s
		AND name IN (
			SELECT parent FROM `tabHas Role` WHERE role = %s
		)
		LIMIT %s
	""", (expiry_date, f"%@{ghost_domain}", settings.ghost_role, batch_size), as_dict=True)

	if not users:
		return

	ghost_names = tuple(u.name for u in users)

	# Safety block: delete from all child tables first
	# The syntax frappe.db.sql(..., (tuple,)) properly interpolates an IN clause.
	
	frappe.db.sql("DELETE FROM `tabHas Role` WHERE parent IN %s", (ghost_names,))
	frappe.db.sql("DELETE FROM `tabUser Email` WHERE parent IN %s", (ghost_names,))
	frappe.db.sql("DELETE FROM `tabBlock Module` WHERE parent IN %s", (ghost_names,))
	frappe.db.sql("DELETE FROM `tabDefaultValue` WHERE parent IN %s", (ghost_names,))
	frappe.db.sql("DELETE FROM `tabUser Social Login` WHERE parent IN %s", (ghost_names,))
	
	# Finally, delete from User table
	frappe.db.sql("DELETE FROM `tabUser` WHERE name IN %s", (ghost_names,))
	
	frappe.db.commit()


def expire_otps():
	"""
	Scheduled function to expire OTPs that have passed their expiry time
	This should be run periodically (e.g., every 5-10 minutes)
	"""
	try:
		expired_otps = frappe.get_all(
			"OTP", filters={"status": "Valid", "expiry": ["<", now_datetime()]}, fields=["name"]
		)

		count = 0
		for otp in expired_otps:
			try:
				otp_doc = frappe.get_doc("OTP", otp.name)
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
	
	leads = frappe.get_all("Ghost Lead", 
		filters={
			"status": "Captured",
			"conversion_reminder_sent": 0,
			"creation": ["<", threshold_date]
		},
		fields=["name", "ghost_email", "captured_email"]
	)
	
	if not leads:
		return
		
	email_template = frappe.get_doc("Email Template", settings.lead_reminder_email_template)
	
	for lead in leads:
		try:
			args = {
				"ghost_email": lead.ghost_email,
				"captured_email": lead.captured_email
			}
			subject = frappe.render_template(email_template.subject, args)
			content = frappe.render_template(email_template.response, args)
			
			frappe.sendmail(
				recipients=[lead.captured_email],
				subject=subject,
				content=content,
				now=True
			)
			
			frappe.db.set_value("Ghost Lead", lead.name, "conversion_reminder_sent", 1)
		except Exception as e:
			frappe.log_error(f"Error sending lead reminder to {lead.captured_email}: {str(e)}", "Lead Reminder")
	
	frappe.db.commit()

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
