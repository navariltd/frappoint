// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room Rate Day", {
	setup(frm) {
		frm.set_query("rate_plan", () => ({ filters: { is_active: 1 } }));
		frm.set_query("room_type", () => ({
			filters: { property: frm.doc.property, is_active: 1 },
		}));
	},
});
