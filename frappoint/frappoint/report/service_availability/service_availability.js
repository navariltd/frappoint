// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Service Availability"] = {
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
			fieldname: "shift_assignment",
			label: __("Shift Assignment"),
			fieldtype: "Link",
			options: "Service Provider Shift Assignment",
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
		},
	],
};
