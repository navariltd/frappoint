// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Cashier Report"] = {
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
			fieldname: "from_date",
			label: __("From Business Date"),
			fieldtype: "Date",
			description: __("Defaults to a week before To Business Date."),
		},
		{
			fieldname: "to_date",
			label: __("To Business Date"),
			fieldtype: "Date",
			description: __("Defaults to the property's business date."),
		},
		{ fieldname: "cashier", label: __("Cashier"), fieldtype: "Link", options: "User" },
	],
};
