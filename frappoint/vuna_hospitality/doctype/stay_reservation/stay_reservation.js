// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const RESERVATION_API = "frappoint.vuna_hospitality.api.reservations";

frappe.ui.form.on("Stay Reservation", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Open in Booking Desk"), () =>
			window.open(
				`/booking_desk/hotel/reservations/${encodeURIComponent(frm.doc.name)}`,
				"_blank"
			)
		);
		if (frm.doc.status === "Held" && frm.doc.hold_expires_at) {
			frm.dashboard.set_headline_alert(
				__("Rooms held until {0}. Confirm before then or the hold is released.", [
					frappe.datetime.str_to_user(frm.doc.hold_expires_at),
				]),
				"orange"
			);
		}
		if (frm.doc.status === "Held") {
			frm.add_custom_button(__("Confirm"), () =>
				run_reservation_command(frm, "confirm_stay", { stay: frm.doc.name })
			).addClass("btn-primary");
		}
		if (["Held", "Confirmed", "Due In"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel Stay"), () =>
				ask_cancel_reason((reason) =>
					run_reservation_command(frm, "cancel_stay", { stay: frm.doc.name, reason })
				)
			);
		}
	},
});

function run_reservation_command(frm, method, args) {
	return frappe
		.call({ method: `${RESERVATION_API}.${method}`, args, freeze: true })
		.then(() => frm.reload_doc());
}

function ask_cancel_reason(callback) {
	frappe.prompt(
		{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		({ reason }) => callback(reason),
		__("Cancel"),
		__("Cancel")
	);
}
