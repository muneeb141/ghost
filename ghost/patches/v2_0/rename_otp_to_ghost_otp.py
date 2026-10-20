"""Preserve Ghost-owned OTP data before the renamed DocType is synchronized."""

import frappe
from frappe.model.rename_doc import rename_doc

OLD = "OTP"
NEW = "Ghost OTP"


def _owned_schema(name):
	row = frappe.db.get_value(
		"DocType", name, ["module", "custom", "issingle", "istable", "is_virtual"], as_dict=True
	)
	if row and (
		row.module != "Ghost" or any(row.get(k) for k in ("custom", "issingle", "istable", "is_virtual"))
	):
		raise frappe.ValidationError(
			f"Cannot migrate Ghost OTP: {name} is not Ghost's standard OTP DocType. "
			"Resolve the ownership conflict on a backup clone before retrying."
		)
	return row


def validate_target():
	"""Also run before fresh installation so model sync cannot overwrite another app."""
	target = _owned_schema(NEW)
	if not target and frappe.db.table_exists(NEW):
		raise frappe.ValidationError("Cannot install Ghost OTP: an unregistered tabGhost OTP table exists.")
	if target and not frappe.db.table_exists(NEW):
		raise frappe.ValidationError("Cannot migrate Ghost OTP: the renamed table is missing.")
	return target


def validate_migration():
	"""Run before migrate as well, so --skip-failing cannot bypass collision checks."""
	target = validate_target()
	source = frappe.db.get_value("DocType", OLD, "module")
	if source and source != "Ghost":
		if target:
			# A different app may legitimately use OTP after Ghost has been renamed.
			return False
		_owned_schema(OLD)  # Raise without modifying the foreign schema.
	if source:
		_owned_schema(OLD)
		if target or frappe.db.table_exists(NEW):
			raise frappe.ValidationError(
				"Cannot migrate Ghost OTP: both OTP and Ghost OTP exist. "
				"Automatic merging is unsafe; restore or resolve the conflict before retrying."
			)
		if not frappe.db.table_exists(OLD):
			raise frappe.ValidationError("Cannot migrate Ghost OTP: the legacy tabOTP table is missing.")
		return True
	if frappe.db.table_exists(OLD):
		raise frappe.ValidationError("Cannot migrate Ghost OTP: an unregistered tabOTP table exists.")
	return False


def execute():
	if not validate_migration():
		return
	# in_patch prevents Frappe from rewriting tracked controller files. Suppress
	# developer-mode exports to other apps while native Link metadata is updated.
	previous_patch = frappe.flags.in_patch
	previous_developer = frappe.conf.developer_mode
	try:
		frappe.flags.in_patch = True
		frappe.conf.developer_mode = 0
		rename_doc(
			"DocType",
			OLD,
			NEW,
			force=True,
			ignore_permissions=True,
			show_alert=False,
			rebuild_search=False,
		)
	finally:
		frappe.flags.in_patch = previous_patch
		frappe.conf.developer_mode = previous_developer
