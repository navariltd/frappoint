// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rate Season", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { is_active: 1 } }));
		frm.set_query("rate_plan", () => ({
			filters: { property: frm.doc.property, rate_basis: "Night", is_active: 1 },
		}));
		frm.set_query("room_type", "rates", () => ({
			filters: { property: frm.doc.property, is_active: 1 },
		}));
	},

	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;
		frm.add_custom_button(__("Generate Rates"), () => {
			frappe.prompt(
				[
					{
						fieldname: "overwrite_manual",
						fieldtype: "Check",
						label: __("Also overwrite rates edited by hand"),
						description: __(
							"Leave unticked to keep manual overrides and only update season-generated rates."
						),
					},
				],
				(values) =>
					frappe
						.xcall(
							"frappoint.vuna_hospitality.services.rates.generate_season_rates",
							{ season: frm.doc.name, overwrite_manual: values.overwrite_manual },
							__("Generating rates...")
						)
						.then((r) => {
							frappe.msgprint(
								__(
									"{0} nights: {1} rates created, {2} updated, {3} manual overrides kept.",
									[r.nights, r.created, r.updated, r.skipped_manual]
								)
							);
							frm.reload_doc();
						}),
				__("Generate Room Rates"),
				__("Generate")
			);
		}).addClass("btn-primary");
		frm.add_custom_button(__("Rates by Night"), () =>
			frappe.set_route("List", "Room Rate Day", { season: frm.doc.name })
		);
	},

	property(frm) {
		frm.set_value("rate_plan", null);
		frm.clear_table("rates");
		frm.refresh_field("rates");
	},
});
