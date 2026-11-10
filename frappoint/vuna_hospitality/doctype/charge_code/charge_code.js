// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Charge Code", {
	setup(frm) {
		frm.set_query("charge_department", () => ({ filters: { is_active: 1 } }));
		frm.set_query("item", () => ({ filters: { disabled: 0 } }));
	},

	code(frm) {
		if (frm.doc.code) frm.set_value("code", frm.doc.code.toUpperCase().trim());
	},
});
