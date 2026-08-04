import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime


@frappe.whitelist()
def get_analytics_data(days=30, from_date=None, to_date=None):
	"""Return conversion analytics for the Ghost Analytics page.

	All metrics are derived from the User table (ghost sessions) and the
	Ghost Conversion Log (conversions).
	"""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	settings = frappe.get_single("Ghost Settings")
	domain = settings.ghost_email_domain or "guest.local"
	ghost_like = f"ghost_%@{domain}"

	try:
		days_int = int(days) if days else 30
	except ValueError:
		days_int = 30

	since = getdate(from_date) if from_date else getdate(add_days(now_datetime(), -days_int))

	total_sessions = frappe.db.count("User", {"email": ["like", ghost_like], "creation": [">=", since]})
	total_conversions = frappe.db.count("Ghost Conversion Log", {"converted_at": [">=", since]})
	conversion_rate = (
		round((total_conversions / total_sessions) * 100, 2) if total_sessions else 0.0
	)
	
	total_leads = 0
	converted_leads = 0
	reminded_leads = 0
	recovered_leads = 0
	if frappe.db.exists("DocType", "Ghost Lead"):
		total_leads = frappe.db.count("Ghost Lead", {"creation": [">=", since]})
		converted_leads = frappe.db.count("Ghost Lead", {"status": "Converted", "modified": [">=", since]})
		reminded_leads = frappe.db.count("Ghost Lead", {"conversion_reminder_sent": 1, "creation": [">=", since]})
		recovered_leads = frappe.db.count("Ghost Lead", {"conversion_reminder_sent": 1, "status": "Converted", "modified": [">=", since]})
		
	lead_conversion_rate = (
		round((converted_leads / total_leads) * 100, 2) if total_leads else 0.0
	)
	reminder_recovery_rate = (
		round((recovered_leads / reminded_leads) * 100, 2) if reminded_leads else 0.0
	)

	avg_duration = frappe.db.sql(
		"SELECT AVG(conversion_duration_ms) FROM `tabGhost Conversion Log` WHERE converted_at >= %s",
		(since,)
	)[0][0]

	total_merged_ghosts = frappe.db.sql(
		"SELECT SUM(merged_ghosts_count) FROM `tabGhost Conversion Log` WHERE converted_at >= %s",
		(since,)
	)[0][0] or 0

	conversions_by_mode = frappe.db.sql(
		"""
		SELECT conversion_mode, COUNT(*) AS count
		FROM `tabGhost Conversion Log`
		WHERE converted_at >= %s
		GROUP BY conversion_mode
		ORDER BY count DESC
		""",
		(since,),
		as_dict=True,
	)

	conversions_by_channel = frappe.db.sql(
		"""
		SELECT COALESCE(conversion_channel, 'OTP') AS channel, COUNT(*) AS count
		FROM `tabGhost Conversion Log`
		WHERE converted_at >= %s
		GROUP BY COALESCE(conversion_channel, 'OTP')
		ORDER BY count DESC
		""",
		(since,),
		as_dict=True,
	)

	sessions_by_day = frappe.db.sql(
		"""
		SELECT DATE(creation) AS day, COUNT(*) AS count
		FROM `tabUser`
		WHERE email LIKE %s AND creation >= %s
		GROUP BY DATE(creation)
		ORDER BY day
		""",
		(ghost_like, since),
		as_dict=True,
	)

	conversions_by_day = frappe.db.sql(
		"""
		SELECT DATE(converted_at) AS day, COUNT(*) AS count
		FROM `tabGhost Conversion Log`
		WHERE converted_at >= %s
		GROUP BY DATE(converted_at)
		ORDER BY day
		""",
		(since,),
		as_dict=True,
	)

	return {
		"logging_enabled": bool(getattr(settings, "enable_conversion_logging", 0)),
		"total_sessions": total_sessions,
		"total_conversions": total_conversions,
		"conversion_rate": conversion_rate,
		"total_leads": total_leads,
		"lead_conversion_rate": lead_conversion_rate,
		"reminder_recovery_rate": reminder_recovery_rate,
		"total_merged_ghosts": int(total_merged_ghosts),
		"avg_conversion_duration_ms": round(avg_duration or 0, 2),
		"conversions_by_mode": conversions_by_mode,
		"conversions_by_channel": conversions_by_channel,
		"daily": {
			"sessions": sessions_by_day,
			"conversions": conversions_by_day,
		},
	}
