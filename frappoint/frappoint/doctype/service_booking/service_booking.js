// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Booking", {
	refresh(frm) {
		if (frm.doc.__onload && frm.doc.__onload.appointment_list_html) {
			frm.get_field("service_appointments").$wrapper.html(
				frm.doc.__onload.appointment_list_html
			);
		} else {
			frm.trigger("render_appointment_list");
		}
	},

	render_appointment_list: function (frm) {
		frappe.call({
			method: "get_appointment_table",
			doc: frm.doc,
			callback: function (r) {
				if (r.message) {
					frm.get_field("service_appointments").$wrapper.html(r.message);
				}
			},
		});
	},
});
