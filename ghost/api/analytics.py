import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime

@frappe.whitelist()
def get_conversion_funnel(from_date=None, to_date=None):
    """
    Exposes conversion funnel metrics for external BI tools.
    Requires 'System Manager' role and 'enable_analytics_api' setting to be enabled.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    settings = frappe.get_single("Ghost Settings")
    
    if not settings.enable_analytics_api:
        frappe.throw(_("Analytics API is not enabled in Ghost Settings."))

    domain = settings.ghost_email_domain or "guest.local"
    ghost_like = f"ghost_%@{domain}"

    # Default to last 30 days if no dates provided
    if not from_date:
        from_date = getdate(add_days(now_datetime(), -30))
    if not to_date:
        to_date = getdate(now_datetime())

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # 1. Total Sessions in period
    total_sessions = frappe.db.count("User", filters={
        "email": ("like", ghost_like),
        "creation": ("between", [from_date, to_date])
    })

    # 2. Total Conversions in period
    total_conversions = frappe.db.count("Ghost Conversion Log", filters={
        "converted_at": ("between", [from_date, to_date])
    })

    # 3. Conversion Rate
    conversion_rate = round((total_conversions / total_sessions) * 100, 2) if total_sessions else 0.0

    # 4. Avg Time to Convert (in ms)
    avg_duration = frappe.db.sql(
        """
        SELECT AVG(conversion_duration_ms) 
        FROM `tabGhost Conversion Log` 
        WHERE converted_at BETWEEN %s AND %s
        """,
        (from_date, to_date)
    )[0][0] or 0.0

    # 5. Conversions by Mode
    conversions_by_mode = frappe.db.sql(
        """
        SELECT conversion_mode, COUNT(*) AS count
        FROM `tabGhost Conversion Log`
        WHERE converted_at BETWEEN %s AND %s
        GROUP BY conversion_mode
        ORDER BY count DESC
        """,
        (from_date, to_date),
        as_dict=True
    )

    # 6. Daily Breakdown
    daily_breakdown = frappe.db.sql(
        """
        SELECT DATE(converted_at) AS day, COUNT(*) AS conversions
        FROM `tabGhost Conversion Log`
        WHERE converted_at BETWEEN %s AND %s
        GROUP BY DATE(converted_at)
        ORDER BY day
        """,
        (from_date, to_date),
        as_dict=True
    )

    return {
        "status": "success",
        "data": {
            "period": {
                "from_date": from_date,
                "to_date": to_date
            },
            "metrics": {
                "total_sessions": total_sessions,
                "total_conversions": total_conversions,
                "conversion_rate": conversion_rate,
                "avg_time_to_convert_ms": round(avg_duration, 2)
            },
            "breakdowns": {
                "conversions_by_mode": conversions_by_mode,
                "daily_conversions": daily_breakdown
            }
        }
    }
