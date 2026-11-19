// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Front Desk Movements"] = {
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
			fieldname: "list",
			label: __("List"),
			fieldtype: "Select",
			options: ["Arrivals", "Departures", "In House", "No Shows", "Cancellations"].join(
				"\n"
			),
			default: "Arrivals",
			reqd: 1,
		},
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			description: __("Defaults to the property's business date."),
		},
	],
};
