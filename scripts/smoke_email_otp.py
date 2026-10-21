"""Exercise native cookie login/replay using a removable fictitious account.

Run from a Bench root with its Python: env/bin/python apps/ghost/scripts/smoke_email_otp.py SITE
Only use an explicitly disposable site. No real OTP delivery occurs.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import frappe
from werkzeug.test import Client
from werkzeug.wrappers import Response

from ghost.ghost.doctype.ghost_otp.ghost_otp import generate


def run(site):
	sites_dir = Path("sites").resolve() if Path("sites/apps.txt").is_file() else Path.cwd()
	if not (sites_dir / "apps.txt").is_file():
		raise RuntimeError("Run from a Bench root or its sites directory")
	os.chdir(sites_dir)
	from frappe.app import application

	sites_path = str(sites_dir)
	email = f"ghost-http-{uuid.uuid4().hex}@example.invalid"
	fields = (
		"enable_otp_login",
		"allow_public_signup",
		"sandbox_mode",
		"max_otp_attempts",
		"enable_ghost_feature",
		"client_id",
		"ghost_role",
		"ghost_email_domain",
		"default_user_role",
		"enable_webhooks",
		"enable_lead_capture",
		"enable_conversion_logging",
	)
	original = None
	otp_name = None
	ghost_data = None
	client_name = None
	ghost_target = "converted-" + email
	try:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		if not frappe.conf.allow_tests:
			raise RuntimeError("Only an explicitly disposable test site is allowed")
		frappe.set_user("Administrator")
		settings = frappe.get_single("Ghost Settings")
		original = {field: settings.get(field) for field in fields}
		client_doc = frappe.get_doc(
			{
				"doctype": "OAuth Client",
				"app_name": email,
				"default_redirect_uri": "https://example.invalid/callback",
				"redirect_uris": "https://example.invalid/callback",
				"scopes": "all",
			}
		).insert()
		client_name = client_doc.name
		settings.update(
			dict(
				enable_otp_login=1,
				allow_public_signup=1,
				sandbox_mode=0,
				max_otp_attempts=5,
				enable_ghost_feature=1,
				client_id=client_name,
				ghost_role="Ghost",
				ghost_email_domain="guest.local",
				default_user_role=None,
				enable_webhooks=0,
				enable_lead_capture=0,
				enable_conversion_logging=0,
			)
		)
		settings.save()
		code = generate(email=email, purpose="Login", send=False)
		otp_name = code["name"]
		ghost_code = generate(email=ghost_target, purpose="Login", send=False)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- guarded disposable-site CLI fixture; see docs/MARKETPLACE_REVIEW.md.
		frappe.destroy()
		client = Client(application, Response, use_cookies=True)
		base = f"http://{site}:8003"
		with patch("frappe.sendmail"):
			response = client.post(
				"/api/method/ghost.api.auth.login",
				json={"email": email, "otp": code["otp_code"]},
				base_url=base,
			)
			assert response.status_code == 200, f"Login HTTP {response.status_code}"
			assert response.json["message"]["user"] == email
			assert "access_token" not in response.json["message"]
			cookies = response.headers.getlist("Set-Cookie")
			assert any(cookie.startswith("sid=") and "HttpOnly" in cookie for cookie in cookies)
			who = client.get("/api/method/frappe.auth.get_logged_user", base_url=base)
			assert who.status_code == 200 and who.json["message"] == email
			other = Client(application, Response, use_cookies=True)
			replay = other.post(
				"/api/method/ghost.api.auth.login",
				json={"email": email, "otp": code["otp_code"]},
				base_url=base,
			)
			assert replay.status_code >= 400, "Consumed OTP authenticated another browser"
			who = other.get("/api/method/frappe.auth.get_logged_user", base_url=base)
			assert who.status_code == 403
		ghost_client = Client(application, Response, use_cookies=True)
		created = ghost_client.post(
			"/api/method/ghost.api.ghost.create_ghost_session", json={}, base_url=base
		)
		assert created.status_code == 200, f"Ghost creation HTTP {created.status_code}"
		ghost_data = created.json["message"]
		converted = ghost_client.post(
			"/api/method/ghost.api.auth.login",
			json={"email": ghost_target, "otp": ghost_code["otp_code"]},
			headers={"Authorization": "Bearer " + ghost_data["access_token"]},
			base_url=base,
		)
		assert converted.status_code == 200, f"Ghost login HTTP {converted.status_code}: {converted.json}"
		assert "access_token" not in converted.json["message"]
		who = ghost_client.get("/api/method/frappe.auth.get_logged_user", base_url=base)
		assert who.status_code == 200 and who.json["message"] == ghost_target
		print("PASS: HTTP owned Ghost conversion establishes the verified cookie session")
		print(
			"PASS: HTTP email OTP login, HttpOnly session, authenticated follow-up, no bearer tokens, cross-browser replay rejected"
		)
	finally:
		frappe.destroy()
		if original is not None:
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			frappe.set_user("Administrator")
			if otp_name:
				frappe.db.delete("Ghost OTP", {"name": otp_name})
			for identity in (email, ghost_target, ghost_data["user"] if ghost_data else None):
				if not identity:
					continue
				frappe.db.delete("Ghost OTP", {"email": identity})
				frappe.db.delete("OAuth Bearer Token", {"user": identity})
				if frappe.db.exists("User", identity):
					frappe.delete_doc("User", identity, force=True, ignore_permissions=True)
			frappe.get_single("Ghost Settings").update(original).save()
			if client_name:
				frappe.delete_doc("OAuth Client", client_name, force=True, ignore_permissions=True)
			frappe.db.commit()  # nosemgrep: frappe-manual-commit -- guarded disposable-site CLI fixture; see docs/MARKETPLACE_REVIEW.md.
			frappe.destroy()


if __name__ == "__main__":
	run(sys.argv[1])
