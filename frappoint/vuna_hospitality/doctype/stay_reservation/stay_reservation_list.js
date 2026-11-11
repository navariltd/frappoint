// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.listview_settings["Stay Reservation"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Held: "orange",
			Confirmed: "blue",
			"Due In": "cyan",
			"In House": "green",
			"Due Out": "yellow",
			"Checked Out": "gray",
			"No Show": "red",
			Cancelled: "red",
			Expired: "gray",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
