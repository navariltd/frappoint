// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

// Sales Partner: link the Supplier that is paid, and bill unbilled commission to it.
const COMMISSION_API = "frappoint.frappoint.api.partner_commission";

frappe.ui.form.on("Sales Partner", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (!frm.doc.custom_supplier && frappe.model.can_create("Supplier")) {
			frm.add_custom_button(
				__("Create Supplier"),
				() =>
					frappe
						.call({
							method: `${COMMISSION_API}.create_partner_supplier`,
							args: { sales_partner: frm.doc.name },
							freeze: true,
						})
						.then(() => frm.reload_doc()),
				__("Commission")
			);
		}

		if (!frappe.model.can_create("Purchase Invoice")) return;
		frappe
			.call({
				method: `${COMMISSION_API}.get_partner_commission_summary`,
				args: { sales_partner: frm.doc.name },
			})
			.then(({ message: rows = [] }) => {
				rows.forEach((row) =>
					frm.dashboard.add_comment(
						__("Unbilled commission in {0}: {1} on {2} invoice(s).", [
							row.company,
							format_currency(row.commission, row.currency),
							row.invoices,
						]),
						row.commission > 0 ? "blue" : "orange",
						true
					)
				);
				if (rows.length && frm.doc.custom_supplier) {
					frm.add_custom_button(
						__("Create Commission Invoice"),
						() => bill_commission(frm, rows),
						__("Commission")
					);
				}
			});
	},
});

function bill_commission(frm, rows) {
	frappe.prompt(
		[
			{
				fieldname: "company",
				fieldtype: "Select",
				label: __("Company"),
				options: rows.map((row) => row.company),
				default: rows[0].company,
				reqd: 1,
			},
			{
				fieldname: "to_date",
				fieldtype: "Date",
				label: __("Commission Up To"),
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
		],
		({ company, to_date }) =>
			frappe
				.call({
					method: `${COMMISSION_API}.create_commission_invoice`,
					args: { sales_partner: frm.doc.name, company, to_date },
					freeze: true,
				})
				.then(({ message }) => frappe.set_route("Form", "Purchase Invoice", message)),
		__("Bill Commission to {0}", [frm.doc.custom_supplier]),
		__("Create Draft Purchase Invoice")
	);
}
