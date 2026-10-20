"""Database fixtures shared by v15 and v16; no ERPNext dependency."""

import uuid
from contextlib import contextmanager

import frappe

try:
	from frappe.tests import IntegrationTestCase
except ImportError:
	from frappe.tests.utils import FrappeTestCase as IntegrationTestCase

from ghost.api.ghost import convert_to_real_user, create_ghost_session
from ghost.ghost.doctype.otp.otp import generate


class GhostIntegrationCase(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.tag = uuid.uuid4().hex
		self.email = f"ghost-test-{self.tag}@example.invalid"
		frappe.local.request_ip = f"ghost-test-{self.tag}"
		if not frappe.db.exists("Role", "Ghost"):
			frappe.get_doc({"doctype": "Role", "role_name": "Ghost", "desk_access": 0}).insert()
		self.client = frappe.get_doc(
			{
				"doctype": "OAuth Client",
				"app_name": self.tag,
				"default_redirect_uri": "https://example.invalid/callback",
				"redirect_uris": "https://example.invalid/callback",
				"scopes": "all",
			}
		).insert()
		self.settings = frappe.get_single("Ghost Settings")
		self.settings.update(
			dict(
				enable_ghost_feature=1,
				ghost_role="Ghost",
				ghost_email_domain=f"{self.tag}.guest.invalid",
				client_id=self.client.name,
				enable_otp_login=1,
				allow_public_signup=1,
				allow_system_user_login=0,
				default_user_role=None,
				sandbox_mode=0,
				enable_auto_cleanup=0,
				enable_lead_capture=0,
				enable_social_login=0,
				enable_magic_link=0,
				enable_multi_device_merge=0,
				enable_webhooks=0,
				enable_realtime_events=0,
				enable_conversion_logging=0,
				enable_analytics_api=0,
				max_otp_attempts=10,
				otp_length=6,
				otp_code_type="Numeric",
				otp_delivery_type="Email",
				expiry_time_minutes=10,
			)
		)
		self.settings.save()
		frappe.clear_document_cache("Ghost Settings", "Ghost Settings")
		self.addCleanup(frappe.set_user, "Administrator")

	def configure(self, **values):
		frappe.set_user("Administrator")
		self.settings = frappe.get_single("Ghost Settings").update(values)
		self.settings.save()
		frappe.clear_document_cache("Ghost Settings", "Ghost Settings")
		return self.settings

	def new_user(self, email=None, role=None):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": email or self.email,
				"first_name": "Fixture",
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}] if role else [],
			}
		).insert(ignore_permissions=True)

	def new_ghost(self, **kwargs):
		return create_ghost_session(**kwargs)

	def code(self, email=None, purpose="Login", **kwargs):
		return generate(email=email or self.email, purpose=purpose, send=False, **kwargs)["otp_code"]

	@contextmanager
	def actor(self, user):
		previous = frappe.session.user
		frappe.set_user(user)
		try:
			yield
		finally:
			frappe.set_user(previous)

	def convert(self, source, target=None, **kwargs):
		target = target or self.email
		code = self.code(target, purpose="Conversion")
		with self.actor(source):
			return convert_to_real_user(source, target, otp_code=code, **kwargs)
