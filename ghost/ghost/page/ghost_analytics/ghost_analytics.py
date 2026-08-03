import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime


@frappe.whitelist()
def get_analytics_data():
	"""Return conversion analytics for the Ghost Analytics page.

	All metrics are derived from the User table (ghost sessions) and the
	Ghost Conversion Log (conversions).
	"""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	settings = frappe.get_single("Ghost Settings")
	domain = settings.ghost_email_domain or "guest.local"
	ghost_like = f"ghost_%@{domain}"

	total_sessions = frappe.db.count("User", {"email": ["like", ghost_like]})
	total_conversions = frappe.db.count("Ghost Conversion Log")
	conversion_rate = (
		round((total_conversions / total_sessions) * 100, 2) if total_sessions else 0.0
	)

	avg_duration = frappe.db.sql(
		"SELECT AVG(conversion_duration_ms) FROM `tabGhost Conversion Log`"
	)[0][0]

	conversions_by_mode = frappe.db.sql(
		"""
		SELECT conversion_mode, COUNT(*) AS count
		FROM `tabGhost Conversion Log`
		GROUP BY conversion_mode
		ORDER BY count DESC
		""",
		as_dict=True,
	)

	since = getdate(add_days(now_datetime(), -30))

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
		"avg_conversion_duration_ms": round(avg_duration or 0, 2),
		"conversions_by_mode": conversions_by_mode,
		"daily": {
			"sessions": sessions_by_day,
			"conversions": conversions_by_day,
		},
	}
