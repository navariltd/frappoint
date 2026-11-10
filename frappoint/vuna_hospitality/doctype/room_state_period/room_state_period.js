// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room State Period", {
	setup(frm) {
		frm.set_query("room", () => ({ filters: { is_active: 1 } }));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.state === "Out of Order") {
			frm.dashboard.set_headline(
				__("Room {0} is removed from sellable inventory for {1} night(s).", [
					frm.doc.room,
					frm.doc.nights,
				])
			);
		}
	},

	from_date: (frm) => frm.trigger("update_nights"),
	to_date: (frm) => frm.trigger("update_nights"),

	update_nights(frm) {
		if (frm.doc.from_date && frm.doc.to_date) {
			frm.set_value("nights", frappe.datetime.get_diff(frm.doc.to_date, frm.doc.from_date));
		}
	},
});
