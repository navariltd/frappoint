// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Guest Relationship", {
	setup(frm) {
		const not_merged_or = (other) => () => ({
			filters: { merged_into: ["is", "not set"], name: ["!=", frm.doc[other] || ""] },
		});
		frm.set_query("guest_profile", not_merged_or("related_guest"));
		frm.set_query("related_guest", not_merged_or("guest_profile"));
	},
});
