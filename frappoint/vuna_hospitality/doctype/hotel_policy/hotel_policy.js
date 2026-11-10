// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hotel Policy", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { is_active: 1 } }));
	},
});
