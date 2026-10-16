// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Service Demand Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: ["Weekly", "Monthly"],
			default: "Weekly",
			reqd: 1,
		},
		{
			fieldname: "week_start",
			label: __("Week Start"),
			fieldtype: "Date",
			default: moment().startOf("isoWeek").format("YYYY-MM-DD"),
			depends_on: 'eval:doc.view === "Weekly"',
			mandatory_depends_on: 'eval:doc.view === "Weekly"',
			description: __(
				"Shows seven days starting on Week Start. Counts Confirmed, Completed or Paid appointments."
			),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: moment().subtract(11, "months").startOf("month").format("YYYY-MM-DD"),
			depends_on: 'eval:doc.view === "Monthly"',
			mandatory_depends_on: 'eval:doc.view === "Monthly"',
			description: __(
				"May be up to 12 months ago. Counts only dates within the selected period."
			),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			depends_on: 'eval:doc.view === "Monthly"',
			mandatory_depends_on: 'eval:doc.view === "Monthly"',
		},
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Link",
			options: "Service Type",
		},
	],
};
