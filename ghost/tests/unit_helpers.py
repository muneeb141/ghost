"""Restore context-local attributes explicitly on both Frappe local implementations."""

from contextlib import contextmanager

import frappe


@contextmanager
def local_attribute(name, value):
	missing = object()
	original = getattr(frappe.local, name, missing)
	setattr(frappe.local, name, value)
	try:
		yield
	finally:
		if original is missing:
			delattr(frappe.local, name)
		else:
			setattr(frappe.local, name, original)
