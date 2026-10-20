from unittest.mock import patch

import frappe

from ghost.tests.helpers import GhostIntegrationCase


class TestMultiDeviceMerge(GhostIntegrationCase):
	def assert_unverified_related_account_is_untouched(self, enabled):
		self.configure(enable_multi_device_merge=enabled, merge_detection_method="Lead Email")
		a = self.new_ghost()["user"]
		b = self.new_ghost()["user"]
		with patch("ghost.api.merge.find_related_ghosts", return_value=[b]) as find:
			result = self.convert(a)
		find.assert_not_called()
		self.assertNotIn("merged_ghosts", result)
		self.assertEqual(frappe.db.get_value("User", b, "enabled"), 1)

	def test_email_matching_does_not_claim_another_device(self):
		self.assert_unverified_related_account_is_untouched(1)

	def test_merge_disabled(self):
		self.assert_unverified_related_account_is_untouched(0)
