// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Service Availability"] = {
	// Rows are grouped Date -> Start Time -> Provider / Service Unit.
	tree: true,
	parent_field: "parent_key",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		return data && data.is_group && column.fieldname === "label"
			? `<strong>${formatted}</strong>`
			: formatted;
	},
	filters: [
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Link",
			options: "Service Type",
			reqd: 1,
		},
		{
			fieldname: "duration",
			label: __("Duration (Minutes)"),
			fieldtype: "Int",
			reqd: 1,
		},
		{
			fieldname: "date_from",
			label: __("Date From"),
			fieldtype: "Date",
		},
		{
			fieldname: "date_to",
			label: __("Date To"),
			fieldtype: "Date",
		},
		{
			fieldname: "start_time_from",
			label: __("Start Time From"),
			fieldtype: "Time",
			description: __("Only show slots starting at or after this time."),
		},
		{
			fieldname: "start_time_to",
			label: __("Start Time To"),
			fieldtype: "Time",
			description: __("Only show slots starting at or before this time."),
		},
		{
			fieldname: "provider",
			label: __("Provider"),
			fieldtype: "Link",
			options: "Service Provider",
		},
		{
			fieldname: "service_unit",
			label: __("Service Unit"),
			fieldtype: "Link",
			options: "Service Unit",
			get_query: () => ({
				filters: { is_group: 0 },
			}),
		},
		{
			fieldname: "gender",
			label: __("Provider Gender"),
			fieldtype: "Link",
			options: "Gender",
		},
		{
			fieldname: "days_ahead",
			label: __("Days Ahead"),
			fieldtype: "Int",
			default: 30,
			description: __("Used when Date To is empty."),
		},
	],
};
