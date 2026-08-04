# Copyright (c) 2026, Ghost and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class GhostConversionLog(Document):
	def validate(self):
		if not self.converted_at:
			self.converted_at = now_datetime()
