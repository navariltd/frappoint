// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["House Position"] = {
	// Each room type shows rooms still available per night; expand it to see why.
	tree: true,
	parent_field: "parent_key",
	initial_depth: 0,
	formatter(value, row, column, data, default_formatter) {
		let formatted = default_formatter(value, row, column, data);
		if (!data) return formatted;
		if (data.is_group || data.is_total) {
			formatted = `<strong>${formatted}</strong>`;
		}
		if (data.is_group && column.fieldtype === "Int" && value !== undefined) {
			const color = value <= 0 ? "var(--red-600)" : value <= 2 ? "var(--orange-600)" : "";
			if (color) formatted = `<span style="color: ${color}">${formatted}</span>`;
		}
		return formatted;
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			description: __("Defaults to the property's business date."),
		},
		{
			fieldname: "days",
			label: __("Nights"),
			fieldtype: "Int",
			default: 14,
			description: __("Number of nights to show (up to 62)."),
		},
		{
			fieldname: "room_type",
			label: __("Room Type"),
			fieldtype: "Link",
			options: "Room Type",
			get_query: () => ({
				filters: { property: frappe.query_report.get_filter_value("property") },
			}),
		},
		{
			fieldname: "show_breakdown",
			label: __("Show Breakdown"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
