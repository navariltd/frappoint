// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const HOUSEKEEPING_CONDITIONS = ["Inspected", "Clean", "Pickup", "Dirty"];

frappe.ui.form.on("Hotel Room", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { is_active: 1 } }));
		frm.set_query("room_type", () => ({
			filters: { property: frm.doc.property, is_active: 1 },
		}));
		frm.set_query("connecting_room", () => ({
			filters: { property: frm.doc.property, name: ["!=", frm.doc.name] },
		}));
		// `features` is a Table MultiSelect (no grid), so the filter goes on the field itself.
		frm.set_query("features", () => ({ filters: { is_active: 1 } }));
	},

	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(
			__("Set Housekeeping Condition"),
			() => {
				frappe.prompt(
					[
						{
							fieldname: "condition",
							fieldtype: "Select",
							label: __("Condition"),
							options: HOUSEKEEPING_CONDITIONS.join("\n"),
							default: frm.doc.housekeeping_condition,
							reqd: 1,
						},
						{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
					],
					(values) =>
						frappe
							.xcall(
								"frappoint.vuna_hospitality.services.rooms.set_housekeeping_condition",
								{
									room: frm.doc.name,
									condition: values.condition,
									reason: values.reason,
								}
							)
							.then(() => frm.reload_doc()),
					__("Set Housekeeping Condition"),
					__("Update")
				);
			},
			__("Actions")
		);

		frm.add_custom_button(
			__("Take Out of Order / Service"),
			() => frappe.new_doc("Room State Period", { room: frm.doc.name }),
			__("Actions")
		);
		frm.add_custom_button(
			__("State Periods"),
			() => frappe.set_route("List", "Room State Period", { room: frm.doc.name }),
			__("View")
		);
	},

	property(frm) {
		frm.set_value("room_type", null);
		frm.set_value("connecting_room", null);
	},
});
