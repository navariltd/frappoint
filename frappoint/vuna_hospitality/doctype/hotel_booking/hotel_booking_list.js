// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.listview_settings["Hotel Booking"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Option: "orange",
			Confirmed: "blue",
			"Partly Cancelled": "yellow",
			Cancelled: "red",
			Closed: "gray",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
