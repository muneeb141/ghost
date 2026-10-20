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

from ghost.ghost.doctype.otp.otp import generate


def run(site):
	sites_dir = Path("sites").resolve() if Path("sites/apps.txt").is_file() else Path.cwd()
	if not (sites_dir / "apps.txt").is_file():
		raise RuntimeError("Run from a Bench root or its sites directory")
	os.chdir(sites_dir)
	from frappe.app import application

	sites_path = str(sites_dir)
	email = f"ghost-http-{uuid.uuid4().hex}@example.invalid"
	fields = ("enable_otp_login", "allow_public_signup", "sandbox_mode", "max_otp_attempts")
	original = None
	otp_name = None
	try:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		if not frappe.conf.allow_tests:
			raise RuntimeError("Only an explicitly disposable test site is allowed")
		frappe.set_user("Administrator")
		settings = frappe.get_single("Ghost Settings")
		original = {field: settings.get(field) for field in fields}
		settings.update(dict(enable_otp_login=1, allow_public_signup=1, sandbox_mode=0, max_otp_attempts=5))
		settings.save()
		code = generate(email=email, purpose="Login", send=False)
		otp_name = code["name"]
		frappe.db.commit()
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
				frappe.db.delete("OTP", {"name": otp_name})
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=True, ignore_permissions=True)
			frappe.get_single("Ghost Settings").update(original).save()
			frappe.db.commit()
			frappe.destroy()


if __name__ == "__main__":
	run(sys.argv[1])
