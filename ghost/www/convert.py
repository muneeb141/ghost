import frappe
from frappe.utils import now_datetime


def get_context(context):
	context.no_header = 1
	context.no_footer = 1
	context.no_breadcrumbs = 1

	settings = frappe.get_single("Ghost Settings")
	context.settings = settings

	token = frappe.form_dict.get("token")
	if not token:
		context.error_message = "No token provided."
		return context

	if not settings.enable_magic_link:
		context.error_message = "Magic Link feature is disabled."
		return context

	token_doc_name = frappe.db.get_value(
		"Ghost Magic Link Token", {"token": token, "status": "Pending"}, "name"
	)

	if not token_doc_name:
		context.error_message = "Invalid or already used token."
		return context

	token_doc = frappe.get_doc("Ghost Magic Link Token", token_doc_name)

	if token_doc.expires_on < now_datetime():
		token_doc.db_set("status", "Expired")
		context.error_message = "This magic link has expired."
		return context

	# Valid token. We pass it to the frontend so the user can click "Confirm".
	context.is_valid = True
	context.token = token
	context.settings = settings

	return context
