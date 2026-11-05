from __future__ import annotations

import frappe

# These fields were removed from the Service Type Unit Type DocType, but Frappe
# never drops columns on migrate. The leftover `capacity` column (default 1) was
# still loaded onto child rows and silently capped Service Unit capacity checks.
ORPHAN_COLUMNS = ("capacity", "auto_assign")


def execute():
	doctype = "Service Type Unit Type"
	if not frappe.db.table_exists(doctype):
		return

	meta_fields = {df.fieldname for df in frappe.get_meta(doctype).fields}
	for column in ORPHAN_COLUMNS:
		if column in meta_fields:
			continue
		if frappe.db.has_column(doctype, column):
			frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
