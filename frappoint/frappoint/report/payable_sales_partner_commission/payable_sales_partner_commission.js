// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Payable Sales Partner Commission"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "sales_partner",
			label: __("Sales Partner"),
			fieldtype: "Link",
			options: "Sales Partner",
		},
	],

	// A checkbox per row, so users can bill only the Sales Invoices they pick.
	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},

	onload(report) {
		if (!frappe.model.can_create("Purchase Invoice")) return;

		report.page.add_inner_button(__("Bill Selected"), () => {
			const sales_invoices = selected_invoices(report);
			if (!sales_invoices.length) {
				frappe.msgprint(__("Tick the Sales Invoices whose commission you want to bill."));
				return;
			}
			confirm_and_bill(
				report,
				__(
					"Bill the commission on {0} selected Sales Invoice(s) as draft Purchase Invoices, one per partner?",
					[sales_invoices.length]
				),
				sales_invoices
			);
		});

		report.page.add_inner_button(__("Bill All Shown"), () =>
			confirm_and_bill(
				report,
				__(
					"Bill all the commission shown to each partner's Supplier as draft Purchase Invoices?"
				)
			)
		);
	},
};

function selected_invoices(report) {
	// Checked row indexes point into report.data; the total row is not part of it.
	return report.datatable.rowmanager
		.getCheckedRows()
		.map((index) => report.data[index])
		.filter((row) => row && row.sales_invoice)
		.map((row) => row.sales_invoice);
}

function confirm_and_bill(report, question, sales_invoices = null) {
	const { company, from_date, to_date } = report.get_values();
	frappe.confirm(question, () =>
		frappe
			.call({
				method: "frappoint.frappoint.api.partner_commission.create_all_commission_invoices",
				args: { company, from_date, to_date, sales_invoices },
				freeze: true,
			})
			.then(({ message }) => {
				show_result(message);
				report.refresh();
			})
	);
}

function show_result({ created = [], skipped = [] }) {
	const esc = frappe.utils.escape_html;
	const made = created
		.map(
			(row) =>
				`<li>${esc(
					row.sales_partner
				)}: <a href="/app/purchase-invoice/${encodeURIComponent(
					row.purchase_invoice
				)}">${esc(row.purchase_invoice)}</a></li>`
		)
		.join("");
	const not_made = skipped
		.map(
			(row) => `<li>${esc(row.sales_partner || row.sales_invoice)}: ${esc(row.reason)}</li>`
		)
		.join("");
	frappe.msgprint({
		title: __("Commission Purchase Invoices"),
		indicator: created.length ? "green" : "orange",
		message:
			(made ? `<p>${__("Draft Purchase Invoices created:")}</p><ul>${made}</ul>` : "") +
				(not_made ? `<p>${__("Not billed:")}</p><ul>${not_made}</ul>` : "") ||
			__("Nothing to bill."),
	});
}
