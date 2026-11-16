// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rate Plan", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { is_active: 1 } }));
		frm.set_query("room_charge_code", () => ({
			filters: { transaction_type: "Revenue", is_active: 1 },
		}));
		frm.set_query("cancellation_policy", () => ({
			filters: { property: frm.doc.property, policy_type: "Cancellation", is_active: 1 },
		}));
		frm.set_query("deposit_policy", () => ({
			filters: { property: frm.doc.property, policy_type: "Deposit", is_active: 1 },
		}));
		frm.set_query("parent_rate_plan", () => ({
			filters: {
				property: frm.doc.property,
				is_active: 1,
				rate_basis: frm.doc.rate_basis || "Night",
				name: ["!=", frm.doc.name || ""],
			},
		}));
		frm.set_query("no_show_policy", () => ({
			filters: { property: frm.doc.property, policy_type: "No-show", is_active: 1 },
		}));
		frm.set_query("early_departure_policy", () => ({
			filters: { property: frm.doc.property, policy_type: "Early Departure", is_active: 1 },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Rates by Night"), () =>
			frappe.set_route("List", "Room Rate Day", { rate_plan: frm.doc.name })
		);
		frm.add_custom_button(__("Seasons"), () =>
			frappe.set_route("List", "Rate Season", { rate_plan: frm.doc.name })
		);
	},

	rate_plan_code(frm) {
		if (frm.doc.rate_plan_code) {
			frm.set_value("rate_plan_code", frm.doc.rate_plan_code.toUpperCase().trim());
		}
	},
});
