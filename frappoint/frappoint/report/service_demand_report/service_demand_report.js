// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Service Demand Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "week_start",
			label: __("Week Start"),
			fieldtype: "Date",
			default: moment().startOf("isoWeek").format("YYYY-MM-DD"),
			reqd: 1,
			description: __("Shows Monday to Sunday of the selected week. Counts Confirmed, Completed or Paid appointments."),
		},
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Link",
			options: "Service Type",
		},
	],
};
