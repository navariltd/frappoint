// Copyright (c) 2025, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Type", {
	setup(frm) {
		frm.appointment_settings = null;

		frm.set_query("item", () => {
			return {
				filters: {
					is_stock_item: 0,
					disabled: 0,
				},
			};
		});
	},

	onload(frm) {
		frm.trigger("load_pricing_settings");
		frm.trigger("setup_field_dependencies");
	},

	refresh(frm) {
		if (!frm.appointment_settings) {
			frm.trigger("load_pricing_settings");
		} else {
			frm.trigger("apply_pricing_settings");
		}
	},

	before_save: function (frm) {
		// Validate before saving
		if (frm.appointment_settings && frm.appointment_settings.use_erpnext_pricing) {
			let has_empty_price_list = false;

			(frm.doc.prices || []).forEach(function (row) {
				if (!row.price_list) {
					has_empty_price_list = true;
				}
			});

			if (has_empty_price_list) {
				frappe.throw(
					__(
						"Price List is mandatory for all price rows when ERPNext Pricing is enabled"
					)
				);
			}
		}
	},

	disabled(frm) {
		if (frm.doc.disabled) {
			frappe.confirm(
				__(
					"Disabling this appointment type will prevent new bookings. Existing appointments will not be affected. Continue?"
				),
				function () {
					// TODO: function to be executed here to disable the appointment type
				},
				function () {
					frm.set_value("disabled", 0);
				}
			);
		}
	},

	default_duration_in_minutes(frm) {
		if (frm.doc.default_duration_in_minutes) {
			if (frm.doc.default_duration_in_minutes <= 0) {
				frappe.msgprint({
					title: __("Invalid Duration"),
					indicator: "red",
					message: __("Duration should be greater than 0 minutes"),
				});
			}

			if (frm.doc.default_duration_in_minutes > 480) {
				frappe.msgprint({
					title: __("Warning"),
					indicator: "orange",
					message: __("Duration exceeds 8 hours. Please verify this is correct."),
				});
			}

			// Show helpful duration message
			frm.trigger("show_duration_helper");
		}
	},

	item(frm) {
		if (frm.doc.item) {
			frappe.db.get_value("Item", frm.doc.item, ["item_name", "item_group"]).then((r) => {
				if (r.message) {
					frm.set_value("item_name", r.message.item_name);
					frm.set_value("item_group", r.message.item_group);
				}
			});
		}
	},

	show_duration_helper(frm) {
		if (frm.doc.default_duration_in_minutes) {
			let hours = Math.floor(frm.doc.default_duration_in_minutes / 60);
			let minutes = frm.doc.default_duration_in_minutes % 60;
			let display = "";

			if (hours > 0) {
				display += `${hours} ${hours === 1 ? "hour" : "hours"}`;
			}
			if (minutes > 0) {
				if (hours > 0) display += " and ";
				display += `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
			}

			frm.set_df_property(
				"default_duration_in_minutes",
				"description",
				`Duration: ${display}`
			);
		}
	},

	load_pricing_settings(frm) {
		frm.call("get_appointment_settings").then((r) => {
			if (r && r.message) {
				frm.appointment_settings = {
					use_erpnext_pricing: r.message.use_erpnext_pricing,
				};
				frm.trigger("apply_pricing_settings");
			}
		});
	},

	apply_pricing_settings(frm) {
		if (!frm.appointment_settings) return;

		let use_erpnext_pricing = frm.appointment_settings.use_erpnext_pricing;

		let prices_grid = frm.fields_dict["prices"].grid;

		if (!prices_grid) return;

		prices_grid.docfields.forEach(function (df) {
			if (df.fieldname === "price_list") {
				df.reqd = use_erpnext_pricing ? 1 : 0;
			}
		});

		frm.fields_dict.prices.grid.toggle_enable("uom", !use_erpnext_pricing);

		frm.set_query("price_list", "prices", function () {
			if (!use_erpnext_pricing) return {};
			return {
				filters: {
					selling: 1,
				},
			};
		});

		prices_grid.refresh();

		frm.refresh_field("prices");
	},

	fetch_and_set_item_price(frm, cdt, cdn, row) {
		frappe.dom.freeze("Fetching Price");

		frm.call("get_applicable_item_price", {
			price_list: row.price_list,
			uom: row.uom,
			date: frappe.datetime.now_date(),
		}).then(
			(r) => {
				frappe.dom.unfreeze();

				if (r.message) {
					if (r.message.price_found) {
						frm.events.apply_fetched_price(frm, cdt, cdn, r.message);
					} else {
						frappe.show_alert({
							message: __("No Item price found for {0} in {1}", [
								frm.doc.item,
								row.price_list,
							]),
							indicator: "orange",
						});
					}
				} else {
					frappe.msgprint({
						title: __("No Price Found"),
						indicator: "orange",
						message: __(
							"No Item Price found for this combination. Please enter manually."
						),
					});
				}
			},
			(err) => {
				frappe.dom.unfreeze();
				frappe.msgprint({
					title: __("Error"),
					indicator: "red",
					message: __("Failed to fetch Item Price. Please try again."),
				});
			}
		);
	},

	apply_fetched_price(frm, cdt, cdn, data) {
		let row = locals[cdt][cdn];

		frappe.model.set_value(cdt, cdn, "rate", data.rate);

		let info_parts = [];
		info_parts.push(__("Rate: {0}", [format_currency(data.rate, data.currency)]));

		frappe.show_alert({
			message: __("Price fetched: {0}", [info_parts.join(", ")]),
			indicator: "green",
		});
	},
});

frappe.ui.form.on("Service Type Price", {
	price_list(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.price_list && frm.doc.item) {
			frm.events.fetch_and_set_item_price(frm, cdt, cdn, row);
		}
	},

	uom(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.price_list && frm.doc.item) {
			frm.events.fetch_and_set_item_price(frm, cdt, cdn, row);
		}
	},

	prices_add(frm, cdt, cdn) {
		frm.trigger("load_pricing_settings");

		const row = locals[cdt][cdn];

		if (!row.duration && frm.doc.default_duration_in_minutes) {
			frappe.model.set_value(cdt, cdn, "duration", frm.doc.default_duration_in_minutes);
		}

		if (frm.doc.item) {
			frappe.db.get_value("Item", frm.doc.item, "stock_uom").then((r) => {
				if (r.message && r.message.stock_uom) {
					setTimeout(() => {
						frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
					}, 200);
				}
			});
		}
	},

	rate(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// validate positive rate
		if (row.rate && row.rate <= 0) {
			frappe.msgprint({
				title: __("Invalid Rate"),
				indicator: "red",
				message: __("Rate must be greater than zero"),
			});
			frappe.model.set_value(cdt, cdn, "rate", 0);
		}

		calculate_amount(frm, cdt, cdn);
	},

	duration(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
});

function calculate_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (row.rate && row.duration) {
		frappe.model.set_value(cdt, cdn, "amount", flt(row.rate) * flt(row.duration));
	}
}
