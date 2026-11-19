// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Charges and Adjustments"] = {
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		return data && data.is_total ? `<strong>${formatted}</strong>` : formatted;
	},
	filters: [
		{
			fieldname: "property",
			label: __("Property"),
			fieldtype: "Link",
			options: "Hotel Property",
			reqd: 1,
			get_query: () => ({ filters: { is_active: 1 } }),
		},
		{
			fieldname: "kind",
			label: __("Show"),
			fieldtype: "Select",
			options: [
				"All charges",
				"Reversals",
				"Manual postings",
				"Adjustments, write-offs and paid-outs",
			].join("\n"),
			default: "All charges",
		},
		{ fieldname: "from_date", label: __("From Business Date"), fieldtype: "Date" },
		{
			fieldname: "to_date",
			label: __("To Business Date"),
			fieldtype: "Date",
			description: __(
				"Defaults to the property's business date; From defaults to a week before."
			),
		},
		{
			fieldname: "charge_code",
			label: __("Charge Code"),
			fieldtype: "Link",
			options: "Charge Code",
		},
	],
};
