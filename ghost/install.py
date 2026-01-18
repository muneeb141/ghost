import frappe

def after_install():
	create_ghost_role()
	setup_default_settings()

def create_ghost_role():
	if not frappe.db.exists("Role", "Ghost"):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": "Ghost",
			"desk_access": 0
		}).insert(ignore_permissions=True)

def setup_default_settings():
	settings = frappe.get_single("Ghost Settings")
	settings.enable_ghost_feature = 1
	settings.enable_auto_cleanup = 1
	settings.ghost_role = "Ghost"
	settings.save()
