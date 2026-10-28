// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Service Demand and Revenue"] = {
	tree: true,
	parent_field: "parent_customer",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		return data && data.is_customer_total ? `<strong>${formatted}</strong>` : formatted;
	},
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Link",
			options: "Service Type",
		},
		{
			fieldname: "status",
			label: __("Appointment Status"),
			fieldtype: "Select",
			options: [
				"",
				"Open",
				"Pending Payment",
				"Confirmed",
				"Checked In",
				"In Progress",
				"Rescheduled",
				"Completed",
				"Closed",
				"No Show",
			],
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
			description: __(
				"Defaults to company currency. Revenue is the grand total of completed appointments, grouped by appointment date.",
			),
		},
	],
};
