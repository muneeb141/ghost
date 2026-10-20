"""Migration preflight guards and the retained Python import contract.

Actual DDL/data/reference preservation is tested by scripts/smoke_otp_rename.py
across two separate migrate invocations, on the development site and both CI jobs.
"""

import importlib
import unittest
from unittest.mock import Mock, patch

import frappe

from ghost.patches.v2_0 import rename_otp_to_ghost_otp as migration
from ghost.tests.unit_helpers import local_attribute


class TestOTPRenameGuards(unittest.TestCase):
	def setUp(self):
		self.db = Mock()
		self.schemas = {}
		self.tables = set()
		self.db.get_value.side_effect = self.schema
		self.db.table_exists.side_effect = self.tables.__contains__
		p = patch.object(frappe, "db", self.db)
		p.start()
		self.addCleanup(p.stop)

	def schema(self, doctype, name, fields, **kwargs):
		row = self.schemas.get(name)
		return row.get(fields) if row and isinstance(fields, str) else row

	def own(self, name):
		self.schemas[name] = frappe._dict(module="Ghost", custom=0, issingle=0, istable=0, is_virtual=0)
		self.tables.add(name)

	def test_fresh_install_is_noop(self):
		with patch.object(migration, "rename_doc") as rename:
			migration.execute()
		rename.assert_not_called()

	def test_completed_rename_is_noop(self):
		self.own("Ghost OTP")
		with patch.object(migration, "rename_doc") as rename:
			migration.execute()
			migration.execute()
		rename.assert_not_called()

	def test_foreign_legacy_schema_is_never_renamed(self):
		self.own("OTP")
		self.schemas["OTP"].module = "Other App"
		with patch.object(migration, "rename_doc") as rename:
			with self.assertRaises(frappe.ValidationError):
				migration.execute()
		rename.assert_not_called()

	def test_foreign_target_is_rejected_before_install_or_migrate(self):
		self.own("Ghost OTP")
		self.schemas["Ghost OTP"].module = "Other App"
		for validate in (migration.validate_target, migration.validate_migration):
			with self.subTest(validate=validate.__name__), self.assertRaises(frappe.ValidationError):
				validate()

	def test_both_owned_doctypes_require_manual_resolution(self):
		self.own("OTP")
		self.own("Ghost OTP")
		with patch.object(migration, "rename_doc") as rename:
			with self.assertRaises(frappe.ValidationError):
				migration.execute()
		rename.assert_not_called()

	def test_orphan_tables_and_missing_source_table_are_rejected(self):
		for tables in ({"OTP"}, {"Ghost OTP"}):
			self.tables.clear()
			self.tables.update(tables)
			with self.subTest(tables=tables), self.assertRaises(frappe.ValidationError):
				migration.validate_migration()
		self.own("OTP")
		self.tables.clear()
		with self.assertRaises(frappe.ValidationError):
			migration.validate_migration()

		self.schemas.clear()
		self.own("Ghost OTP")
		self.tables.clear()
		with self.assertRaises(frappe.ValidationError):
			migration.validate_target()

	def test_custom_legacy_schema_is_rejected(self):
		self.own("OTP")
		self.schemas["OTP"].custom = 1
		with self.assertRaises(frappe.ValidationError):
			migration.validate_migration()

	def test_foreign_otp_can_coexist_after_successful_rename(self):
		self.own("Ghost OTP")
		self.own("OTP")
		self.schemas["OTP"].module = "Other App"
		with patch.object(migration, "rename_doc") as rename:
			migration.execute()
		rename.assert_not_called()

	def test_native_rename_does_not_export_sources_and_restores_flags_on_failure(self):
		self.own("OTP")

		def fail(*args, **kwargs):
			self.assertTrue(frappe.flags.in_patch)
			self.assertFalse(frappe.conf.developer_mode)
			raise RuntimeError("simulated native failure")

		with (
			local_attribute("flags", frappe._dict(in_patch=False)),
			local_attribute("conf", frappe._dict(developer_mode=1)),
			patch.object(migration, "rename_doc", side_effect=fail),
		):
			with self.assertRaises(RuntimeError):
				migration.execute()
			self.assertFalse(frappe.flags.in_patch)
			self.assertEqual(frappe.conf.developer_mode, 1)

	def test_old_controller_import_is_the_same_module(self):
		legacy = importlib.import_module("ghost.ghost.doctype.otp.otp")
		current = importlib.import_module("ghost.ghost.doctype.ghost_otp.ghost_otp")
		self.assertIs(legacy, current)
		self.assertIs(legacy.OTP, current.GhostOTP)
		self.assertIs(legacy.generate, current.generate)
