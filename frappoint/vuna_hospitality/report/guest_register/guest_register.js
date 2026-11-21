// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.query_reports["Guest Register"] = {
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
			label: __("From Arrival"),
			fieldtype: "Date",
			description: __("Defaults to a week before To Arrival."),
		},
		{
			fieldname: "to_date",
			label: __("To Arrival"),
			fieldtype: "Date",
			description: __("Defaults to the property's business date."),
		},
	],
	onload(report) {
		// The full register, with document numbers, for the authorities. The server checks the
		// role and records the export.
		report.page.add_inner_button(__("Export for the authorities"), () => {
			const filters = report.get_values();
			if (!filters || !filters.property) return;
			const today = frappe.datetime.get_today();
			const to = filters.to_date || today;
			const from = filters.from_date || frappe.datetime.add_days(to, -6);
			frappe.confirm(
				__(
					"Download the register from {0} to {1} with full document numbers? The export is recorded.",
					[frappe.datetime.str_to_user(from), frappe.datetime.str_to_user(to)]
				),
				() => {
					const query = new URLSearchParams({
						property: filters.property,
						from_date: from,
						to_date: to,
					});
					window.open(
						`/api/method/frappoint.vuna_hospitality.api.guest_register.export_guest_register?${query}`
					);
				}
			);
		});
	},
};
