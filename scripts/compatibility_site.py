"""CI-only clean-install/upgrade assertions; refuses ordinary site names.

Run with the Bench Python from its root. The seed stage uses the previous code,
then the upgrade stage uses the candidate and the migrated real database.
"""

import os
import sys
from pathlib import Path

import frappe

SOURCE = "ghost_deadbeef@guest.local"
TARGET = "ghost-ci-target@example.invalid"
LEAD = "ghost-ci-upgrade-lead"
OTP = "ghost-ci-upgrade-otp"


def check_schema():
	assert set(frappe.get_installed_apps()) == {"frappe", "ghost"}, "Ghost must work without ERPNext"
	assert frappe.db.exists("DocType", "Ghost OTP"), "The renamed Ghost OTP DocType must be installed"
	assert frappe.get_meta("Ghost OTP").module == "Ghost"
	assert not frappe.db.exists("DocType", "OTP")
	assert not frappe.db.table_exists("OTP")
	for operation in ("read", "create", "write"):
		assert not frappe.has_permission("Ghost OTP", operation, user="Guest")
	assert frappe.db.exists("Role", "Ghost")
	assert not frappe.db.get_value("Role", "Ghost", "desk_access")


def fresh():
	check_schema()
	settings = frappe.get_single("Ghost Settings")
	for flag in (
		"enable_ghost_feature",
		"enable_otp_login",
		"allow_public_signup",
		"allow_system_user_login",
		"sandbox_mode",
	):
		assert not settings.get(flag), flag
	print("PASS: Frappe-only fresh install, native OTP schema, restricted permissions and safe defaults")


def seed():
	from frappe.utils import add_to_date, now_datetime

	client = frappe.get_doc(
		{
			"doctype": "OAuth Client",
			"app_name": "Ghost CI upgrade",
			"default_redirect_uri": "https://example.invalid/callback",
			"redirect_uris": "https://example.invalid/callback",
			"scopes": "all",
		}
	).insert()
	settings = frappe.get_single("Ghost Settings")
	settings.update(
		{
			"enable_ghost_feature": 1,
			"ghost_role": "Ghost",
			"client_id": client.name,
			"enable_auto_cleanup": 0,
			"enable_multi_device_merge": 0,
			"enable_webhooks": 0,
			"enable_lead_capture": 0,
			"enable_conversion_logging": 0,
			"sandbox_mode": 1,
			"sandbox_otp": "000141",
		}
	)
	settings.save()
	# Exercise the legacy insecure values as persisted by the previous release.
	frappe.db.set_single_value("Ghost Settings", "verify_otp_on_conversion", 0)
	frappe.db.set_single_value("Ghost Settings", "invalidate_ghost_tokens_on_conversion", 0)
	frappe.get_doc(
		{
			"doctype": "User",
			"email": SOURCE,
			"first_name": "Legacy anonymous",
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "Website User",
			"roles": [{"role": "Ghost"}],
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Ghost Lead",
			"name": LEAD,
			"ghost_email": SOURCE,
			"captured_email": TARGET,
			"status": "Captured",
		}
	).insert(set_name=LEAD)
	frappe.get_doc(
		{
			"doctype": "OTP",
			"name": OTP,
			"otp_code": "123456",
			"email": TARGET,
			"user": SOURCE,
			"purpose": "Login",
			"delivery_method": "Email",
			"status": "Valid",
			"expiry": add_to_date(now_datetime(), minutes=10),
		}
	).insert(set_name=OTP)
	print("PASS: previous public code persisted legacy user, OTP, linked lead and settings")


def upgrade():
	from ghost.api.ghost import convert_to_real_user
	from ghost.ghost.doctype.ghost_otp.ghost_otp import generate, verify

	check_schema()
	settings = frappe.get_single("Ghost Settings")
	assert settings.verify_otp_on_conversion and settings.invalidate_ghost_tokens_on_conversion
	assert not settings.sandbox_mode
	assert not settings.enable_otp_login and not settings.allow_public_signup
	assert frappe.db.exists("User", SOURCE)
	assert frappe.db.get_value("Ghost OTP", OTP, "user") == SOURCE
	assert frappe.db.get_value("Ghost Lead", LEAD, "ghost_email") == SOURCE
	settings.update({"enable_otp_login": 1, "allow_public_signup": 1})
	settings.save()
	assert verify("123456", email=TARGET, purpose="Login")[
		"valid"
	], "A legitimate legacy OTP must remain usable"
	code = generate(email=TARGET, purpose="Conversion", send=False)["otp_code"]
	frappe.set_user(SOURCE)
	try:
		convert_to_real_user(SOURCE, TARGET, bypass_otp=True)
	except frappe.PermissionError:
		pass
	else:
		raise AssertionError("Legacy verification bypass survived the upgrade")
	result = convert_to_real_user(SOURCE, TARGET, otp_code=code)
	assert result["user"] == TARGET
	assert frappe.db.get_value("Ghost Lead", LEAD, "ghost_email") == TARGET
	assert frappe.db.get_value("Ghost OTP", OTP, "user") == TARGET
	print(
		"PASS: legacy records preserved, security defaults migrated, eight-character Ghost identity converted and native User links followed"
	)


def run(site, stage):
	if not site.startswith("ghost-ci-") or stage not in ("fresh", "seed", "upgrade"):
		raise ValueError("Only a dedicated ghost-ci-* site and a known stage are allowed")
	sites_path = Path("sites").resolve()
	os.chdir(sites_path)
	frappe.init(site=site, sites_path=str(sites_path))
	frappe.connect()
	try:
		if not frappe.conf.allow_tests:
			raise ValueError("The CI site must explicitly allow tests")
		frappe.set_user("Administrator")
		globals()[stage]()
		frappe.db.commit()
	except BaseException:
		frappe.db.rollback()
		raise
	finally:
		frappe.destroy()


if __name__ == "__main__":
	run(*sys.argv[1:])
