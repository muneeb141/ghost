import frappe
from frappe.utils import add_days, now_datetime

def delete_expired_ghost_users():
	"""
	Deletes Ghost users that have exceeded the expiration days.
	"""
	settings = frappe.get_single("Ghost Settings")
	if not settings.enable_ghost_feature or not settings.enable_auto_cleanup:
		return

	expiration_days = settings.expiration_days or 30
	# Safety check: Don't allow very short expiration by mistake, unless 0 (immediate? No, 0 usually means disable or massive bug risk).
	if expiration_days < 1:
		expiration_days = 1

	expiry_date = add_days(now_datetime(), -expiration_days)
	ghost_domain = settings.ghost_email_domain or "guest.local"

	# Find users to delete
	# Criteria:
	# 1. Role contains 'Ghost' (Checked via User Role usually, but checking query is faster)
	# 2. Email ends with ghost domain
	# 3. Creation < expiry_date
	# 4. Filter by specific 'Ghost' role to be safe.
	
	users = frappe.db.sql("""
		SELECT name FROM `tabUser`
		WHERE creation < %s
		AND email LIKE %s
		AND name IN (
			SELECT parent FROM `tabHas Role` WHERE role = %s
		)
	""", (expiry_date, f"%@{ghost_domain}", settings.ghost_role), as_dict=True)

	for u in users:
		# Use frappe.delete_doc to ensure strict cleanup (links etc)
		# This might be slow if there are thousands. 
		# For extreme scalability, we might use bulk delete if no important links exist.
		# But standard delete is safer for now.
		try:
			frappe.delete_doc("User", u.name, ignore_permissions=True, force=1)
			# Commit every 100 to avoid long transaction? 
			# frappe.db.commit() # optional, depends on volume
		except Exception:
			frappe.log_error(f"Failed to delete ghost user {u.name}", "Ghost Cleanup")


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
