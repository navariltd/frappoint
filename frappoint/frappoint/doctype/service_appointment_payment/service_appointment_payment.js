// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Appointment Payment", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.reference_doctype === "Service Booking") {
			frm.add_custom_button(__("Get Appointments"), () => {
				frm.call("get_references").then(() => {
					frm.refresh_field("references");
				});
			});
		}

		frm.set_query("reference_doctype", () => {
			return {
				filters: {
					name: ["in", ["Service Booking", "Service Appointment"]],
				},
			};
		});

		frm.set_query("reference_doctype", "references", () => {
			return {
				filters: {
					name: ["in", ["Service Appointment"]],
				},
			};
		});
	},

	reference_docname: function (frm) {
		if (frm.doc.reference_docname) {
			frm.call("get_reference_details").then(() => {
				frm.refresh_fields(["amount", "currency"]);
			});
		}
	},
});
