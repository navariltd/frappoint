// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Guest Ledger"] = {
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
			fieldname: "group",
			label: __("Ledger"),
			fieldtype: "Select",
			options: [
				"",
				"In house",
				"Before arrival",
				"Departed",
				"House accounts",
				"Settlement pending",
			].join("\n"),
		},
	],
};
