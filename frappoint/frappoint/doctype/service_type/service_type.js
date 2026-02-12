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
		frm.trigger("setup_field_dependencies");
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
});

frappe.ui.form.on("Service Type Price", {
	prices_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (!row.duration && frm.doc.default_duration_in_minutes) {
			frappe.model.set_value(cdt, cdn, "duration", frm.doc.default_duration_in_minutes);
		}
	},

	amount(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// validate positive amount
		if (row.amount && row.amount <= 0) {
			frappe.msgprint({
				title: __("Invalid Amount"),
				indicator: "red",
				message: __("Amount must be greater than zero"),
			});
			frappe.model.set_value(cdt, cdn, "amount", 0);
		}
	},
});
