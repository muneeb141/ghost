import frappe
from frappe.model.document import Document
from frappe import _

class GhostSettings(Document):
	def validate(self):
		"""Validate Ghost Settings before saving"""
		# Ensure defaults are set for OAuth token settings
		self.set_default_values()
		
		# Validate OAuth Client ID when ghost feature is enabled
		if self.enable_ghost_feature and not self.client_id:
			frappe.throw(_("OAuth Client ID is required when Ghost Feature is enabled. Please create an OAuth Client first."))
		
		# Validate token expiration values
		if self.access_token_expiry_seconds and self.access_token_expiry_seconds < 300:
			frappe.throw(_("Access Token Expiry should be at least 300 seconds (5 minutes) for security."))
		
		if self.refresh_token_expiry_days and self.refresh_token_expiry_days < 1:
			frappe.throw(_("Refresh Token Expiry should be at least 1 day."))

		# Sandbox mode validation
		if getattr(self, "sandbox_mode", 0) and not getattr(self, "sandbox_otp", None):
			frappe.throw(_("Sandbox OTP Code is required when Sandbox Mode is enabled."))
	
	def set_default_values(self):
		"""Set default values for OAuth settings if not already set"""
		# This ensures defaults work even if the single doctype was created before these fields existed
		if not self.access_token_expiry_seconds:
			self.access_token_expiry_seconds = 3600  # 1 hour
		
		if not self.refresh_token_expiry_days:
			self.refresh_token_expiry_days = 30  # 30 days
		
		if not self.ghost_token_scope:
			self.ghost_token_scope = "all"
		
		# Set invalidate_ghost_tokens_on_conversion to 1 if not set
		if self.invalidate_ghost_tokens_on_conversion is None:
			self.invalidate_ghost_tokens_on_conversion = 1
		
		# Set OTP defaults if not set
		if not self.expiry_time_minutes:
			self.expiry_time_minutes = 10
		
		if not self.max_otp_attempts:
			self.max_otp_attempts = 5
		
		if not self.otp_length:
			self.otp_length = 6
		
		if not self.otp_code_type:
			self.otp_code_type = "Numeric"
		
		if not self.otp_delivery_type:
			self.otp_delivery_type = "Email"

		# Sandbox defaults
		if not getattr(self, "sandbox_otp", None):
			self.sandbox_otp = "000141"
