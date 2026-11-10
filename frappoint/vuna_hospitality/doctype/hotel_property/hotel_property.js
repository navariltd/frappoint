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
		frm.add_custom_button(
			__("House Position"),
			() => frappe.set_route("query-report", "House Position", { property: frm.doc.name }),
			__("View")
		);
		if (frappe.user.has_role(["System Manager", "Hospitality Manager"])) {
			frm.add_custom_button(
				__("Rebuild Inventory"),
				() =>
					frappe
						.xcall(
							"frappoint.vuna_hospitality.services.inventory.rebuild_property_inventory",
							{ property_name: frm.doc.name },
							__("Rebuilding room inventory...")
						)
						.then((result) =>
							frappe.msgprint(
								__(
									"Checked {0} room-type nights: {1} created, {2} corrected. Rows still differing: {3}.",
									[
										result.rows,
										result.created,
										result.updated,
										result.drift_after,
									]
								)
							)
						),
				__("Actions")
			);
		}
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
