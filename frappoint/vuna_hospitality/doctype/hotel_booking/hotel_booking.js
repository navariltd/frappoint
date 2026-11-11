// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const BOOKING_API = "frappoint.vuna_hospitality.api.reservations";

frappe.ui.form.on("Hotel Booking", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Open in Booking Desk"), () =>
			window.open(
				`/booking_desk/hotel/bookings/${encodeURIComponent(frm.doc.name)}`,
				"_blank"
			)
		);
		frappe.db
			.get_list("Stay Reservation", {
				filters: { hotel_booking: frm.doc.name },
				fields: ["status"],
				limit: 0,
			})
			.then((stays) => {
				const statuses = stays.map((stay) => stay.status);
				if (statuses.includes("Held")) {
					frm.add_custom_button(__("Confirm Held Stays"), () =>
						call_booking(frm, "confirm_booking", {})
					).addClass("btn-primary");
				}
				if (statuses.some((s) => ["Held", "Confirmed", "Due In"].includes(s))) {
					frm.add_custom_button(__("Cancel Booking"), () =>
						frappe.prompt(
							{
								fieldname: "reason",
								fieldtype: "Small Text",
								label: __("Reason"),
								reqd: 1,
							},
							({ reason }) => call_booking(frm, "cancel_booking", { reason }),
							__("Cancel Booking"),
							__("Cancel Booking")
						)
					);
				}
			});
	},
});

function call_booking(frm, method, args) {
	return frappe
		.call({
			method: `${BOOKING_API}.${method}`,
			args: { booking: frm.doc.name, ...args },
			freeze: true,
		})
		.then(() => frm.reload_doc());
}
