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
			fieldname: "gender",
			label: __("Provider Gender"),
			fieldtype: "Data",
		},
		{
			fieldname: "days_ahead",
			label: __("Days Ahead"),
			fieldtype: "Int",
			default: 30,
		},
	],
};
