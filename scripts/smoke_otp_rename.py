"""Real, committed fixtures across an actual OTP -> Ghost OTP schema migration.

Run from the Bench root: env/bin/python apps/ghost/scripts/smoke_otp_rename.py SITE seed
Then migrate twice and run the same command with check, followed by cleanup.
Seed runs on the old schema, including from a copied script on the public release.
Only explicitly allowed disposable sites with allow_tests may run these fixtures.
"""

import json
import os
import sys
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime

PREFIX = "ghost-rename-upgrade-probe"
NOTE = "ghost_rename_upgrade_note"
LINK = "ghost_rename_upgrade_link"
EMAIL = "ghost-rename-upgrade@example.invalid"
CODE = "615924"


def insert(doctype, name, **values):
	# A plain Document lets this copied fixture run on the legacy schema even
	# after the checked-out controller already uses the new backing table.
	return Document({"doctype": doctype, **values}).insert(set_name=name, ignore_permissions=True)


def seed():
	assert frappe.db.exists("DocType", "OTP")
	assert frappe.get_meta("OTP").module == "Ghost"
	assert not frappe.db.exists("DocType", "Ghost OTP")
	for dt in ("ToDo", "OTP", "File", "Version", "Comment", "DocShare"):
		assert not frappe.db.exists(dt, PREFIX), f"Refusing to replace existing {dt} fixture"
	for dt, field in (("OTP", NOTE), ("ToDo", LINK)):
		assert not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": field})
	assert not frappe.db.exists("Property Setter", {"doc_type": "OTP", "field_name": NOTE})
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "OTP",
			"fieldname": NOTE,
			"label": "Ghost rename upgrade probe",
			"fieldtype": "Data",
			"insert_after": "phone",
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "ToDo",
			"fieldname": LINK,
			"label": "Ghost OTP upgrade probe",
			"fieldtype": "Link",
			"options": "OTP",
			"insert_after": "description",
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Property Setter",
			"doc_type": "OTP",
			"field_name": NOTE,
			"doctype_or_field": "DocField",
			"property": "description",
			"property_type": "Text",
			"value": "Retain this customization",
		}
	).insert()
	# Include a native naming-series allocation in the snapshot; the migration must not reset it.
	from frappe.model.naming import make_autoname

	series_name = make_autoname("OTP-.YYYY.-.MM.-.DD.-.###.")
	series_key = series_name.rsplit("-", 1)[0] + "-"
	series_value = frappe.db.sql("select current from tabSeries where name=%s", (series_key,))[0][0]
	insert(
		"OTP",
		PREFIX,
		otp_code=CODE,
		email=EMAIL,
		user="Administrator",
		purpose="Login",
		delivery_method="Email",
		status="Valid",
		expiry=add_to_date(now_datetime(), minutes=60),
		**{NOTE: "persisted custom value"},
	)
	snapshot = frappe.get_doc("OTP", PREFIX).as_dict()
	fields = (
		"name",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"otp_code",
		"email",
		"phone",
		"user",
		"purpose",
		"delivery_method",
		"expiry",
		"status",
		"naming_series",
		NOTE,
	)
	payload = {
		"record": {k: str(snapshot.get(k)) for k in fields},
		"series_key": series_key,
		"series_value": int(series_value),
		"row_count": frappe.db.count("OTP"),
	}
	insert(
		"ToDo",
		PREFIX,
		description=json.dumps(payload),
		reference_type="OTP",
		reference_name=PREFIX,
		**{LINK: PREFIX},
	)
	insert(
		"File",
		PREFIX,
		file_name="ghost-rename-probe.txt",
		file_url="https://example.invalid/ghost-rename-probe.txt",
		is_private=1,
		attached_to_doctype="OTP",
		attached_to_name=PREFIX,
	)
	insert("Version", PREFIX, ref_doctype="OTP", docname=PREFIX, data='{"changed": []}')
	insert(
		"Comment",
		PREFIX,
		comment_type="Comment",
		reference_doctype="OTP",
		reference_name=PREFIX,
		content="Ghost rename migration probe",
	)
	insert("DocShare", PREFIX, user="Administrator", share_doctype="OTP", share_name=PREFIX, read=1)
	print(
		"PASS: persisted legacy OTP, row snapshot, series, custom fields, property setter, links, file, version, comment and share"
	)


def check():
	from ghost.ghost.doctype.ghost_otp.ghost_otp import verify
	from ghost.ghost.doctype.otp.otp import generate as legacy_generate
	from ghost.patches.v2_0.rename_otp_to_ghost_otp import execute

	assert frappe.db.exists("DocType", "Ghost OTP")
	assert not frappe.db.exists("DocType", "OTP")
	assert not frappe.db.table_exists("OTP")
	assert frappe.db.table_exists("Ghost OTP")
	payload = json.loads(frappe.db.get_value("ToDo", PREFIX, "description"))
	row = frappe.get_doc("Ghost OTP", PREFIX)
	assert {k: str(row.get(k)) for k in payload["record"]} == payload["record"], "OTP values changed"
	assert (
		frappe.db.count("Ghost OTP") == payload["row_count"]
	), "OTP rows were added or lost during migration"
	for field, value in (("reference_type", "Ghost OTP"), ("reference_name", PREFIX), (LINK, PREFIX)):
		assert frappe.db.get_value("ToDo", PREFIX, field) == value
	assert frappe.db.get_value("Custom Field", {"dt": "ToDo", "fieldname": LINK}, "options") == "Ghost OTP"
	assert frappe.get_meta("Ghost OTP").get_field(NOTE).description == "Retain this customization"
	assert frappe.db.get_value("Custom Field", {"dt": "Ghost OTP", "fieldname": NOTE}, "fieldtype") == "Data"
	for dt, field, namefield in (
		("File", "attached_to_doctype", "attached_to_name"),
		("Version", "ref_doctype", "docname"),
		("Comment", "reference_doctype", "reference_name"),
		("DocShare", "share_doctype", "share_name"),
	):
		assert frappe.db.get_value(dt, PREFIX, field) == "Ghost OTP", (dt, field)
		assert frappe.db.get_value(dt, PREFIX, namefield) == PREFIX, (dt, namefield)
	assert (
		int(frappe.db.sql("select current from tabSeries where name=%s", (payload["series_key"],))[0][0])
		== payload["series_value"]
	)
	for operation in ("read", "create", "write"):
		permission = frappe.has_permission("Ghost OTP", operation, user="Guest")
		assert not permission
	execute()
	execute()
	# Verify the real migrated code using production validation; do not log the code.
	assert verify(CODE, email=EMAIL, purpose="Login")["valid"]
	try:
		verify(CODE, email=EMAIL, purpose="Login")
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("Migrated OTP was replayable")
	from ghost.ghost.doctype.ghost_otp.ghost_otp import generate

	assert legacy_generate is generate
	print(
		"PASS: migrated rows/values/series/customizations/native references retained; repeat migration safe; legacy import works; active OTP consumed exactly once"
	)


def cleanup():
	for dt in ("ToDo", "File", "Version", "Comment", "DocShare"):
		frappe.db.delete(dt, {"name": PREFIX})
	for dt in ("OTP", "Ghost OTP"):
		if frappe.db.exists("DocType", dt) and frappe.get_meta(dt).module == "Ghost":
			frappe.db.delete(dt, {"name": PREFIX})
			for row in frappe.get_all("Property Setter", {"doc_type": dt, "field_name": NOTE}, pluck="name"):
				frappe.delete_doc("Property Setter", row, ignore_permissions=True)
	for dt, field in (("OTP", NOTE), ("Ghost OTP", NOTE), ("ToDo", LINK)):
		for row in frappe.get_all("Custom Field", {"dt": dt, "fieldname": field}, pluck="name"):
			frappe.delete_doc("Custom Field", row, ignore_permissions=True)
	frappe.clear_cache()
	print("PASS: removed only named rename-test records and metadata fixtures")


def run(site, stage):
	if site != "ecom.localhost" and not site.startswith("ghost-ci-"):
		raise ValueError("Only the authorized disposable development or CI sites are allowed")
	if stage not in ("seed", "check", "cleanup"):
		raise ValueError("Expected seed, check or cleanup")
	sites_path = Path("sites").resolve()
	os.chdir(sites_path)
	frappe.init(site=site, sites_path=str(sites_path))
	frappe.connect()
	try:
		if not frappe.conf.allow_tests:
			raise ValueError("The fixture requires allow_tests on a disposable site")
		frappe.set_user("Administrator")
		globals()[stage]()
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- guarded disposable-site CLI fixture; see docs/MARKETPLACE_REVIEW.md.
	except BaseException:
		frappe.db.rollback()
		raise
	finally:
		frappe.destroy()


if __name__ == "__main__":
	run(*sys.argv[1:])
