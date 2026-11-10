// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const HOTEL_PROPERTY_ACCOUNT_FIELDS = [
	"guest_ledger_account",
	"advance_account",
	"room_post_clearing_account",
	"breakage_income_account",
	"cash_over_short_account",
];

frappe.ui.form.on("Hotel Property", {
	setup(frm) {
		HOTEL_PROPERTY_ACCOUNT_FIELDS.forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0 },
			}));
		});
		frm.set_query("default_cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	onload(frm) {
		frappe
			.xcall(
				"frappoint.vuna_hospitality.doctype.hotel_property.hotel_property.get_time_zones"
			)
			.then((zones) => frm.set_df_property("time_zone", "options", zones));
		if (frm.is_new() && !frm.doc.time_zone) {
			frm.set_value("time_zone", frappe.boot.time_zone?.system);
		}
	},

	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Rooms"),
			() => frappe.set_route("List", "Hotel Room", { property: frm.doc.name }),
			__("View")
		);
		frm.add_custom_button(
			__("Room Types"),
			() => frappe.set_route("List", "Room Type", { property: frm.doc.name }),
			__("View")
		);
	},

	property_code(frm) {
		if (frm.doc.property_code) {
			frm.set_value("property_code", frm.doc.property_code.toUpperCase().trim());
		}
	},

	company(frm) {
		HOTEL_PROPERTY_ACCOUNT_FIELDS.concat(["default_cost_center"]).forEach((fieldname) =>
			frm.set_value(fieldname, null)
		);
	},
});
