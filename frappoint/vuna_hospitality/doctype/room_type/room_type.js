// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Type", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { is_active: 1 } }));
		// `amenities` is a Table MultiSelect (no grid), so the filter goes on the field itself.
		frm.set_query("amenities", () => ({ filters: { is_active: 1 } }));
	},

	code(frm) {
		if (frm.doc.code) {
			frm.set_value("code", frm.doc.code.toUpperCase().trim());
		}
	},
});
