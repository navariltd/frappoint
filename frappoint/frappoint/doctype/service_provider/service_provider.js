// Copyright (c) 2025, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Provider", {
	setup(frm) {
		frm.set_query("google_calendar", function () {
			return {
				filters: {
					enable: true,
					owner: frm.doc.user,
				},
			};
		});
	},

	user(frm) {
		if (frm.doc.user) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "User",
					name: frm.doc.user,
				},
				callback: function (data) {
					frappe.model.get_value(
						"Employee",
						{ user_id: frm.doc.user },
						"name",
						function (data) {
							if (data) {
								if (!frm.doc.employee || frm.doc.employee != data.name)
									frappe.model.set_value(
										frm.doctype,
										frm.docname,
										"employee",
										data.name
									);
							} else {
								frappe.model.set_value(frm.doctype, frm.docname, "employee", "");
							}
						}
					);

					if (!frm.doc.first_name || frm.doc.first_name != data.message.first_name)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"first_name",
							data.message.first_name
						);
					if (!frm.doc.middle_name || frm.doc.middle_name != data.message.middle_name)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"middle_name",
							data.message.middle_name
						);
					if (!frm.doc.last_name || frm.doc.last_name != data.message.last_name)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"last_name",
							data.message.last_name
						);
					if (!frm.doc.mobile_no || frm.doc.mobile_no != data.message.mobile_no)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"mobile_no",
							data.message.mobile_no
						);
				},
			});
		}
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Employee",
					name: frm.doc.employee,
				},
				callback: function (data) {
					if (!frm.doc.user || frm.doc.user != data.message.user_id)
						frm.set_value("user", data.message.user_id);
					if (!frm.doc.designation || frm.doc.designation != data.message.designation)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"designation",
							data.message.designation
						);
					if (!frm.doc.grade || frm.doc.grade != data.message.grade)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"grade",
							data.message.grade
						);
					if (!frm.doc.first_name || !frm.doc.user) {
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"first_name",
							data.message.first_name
						);
						frappe.model.set_value(frm.doctype, frm.docname, "middle_name", "");
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"last_name",
							data.message.last_name
						);
					}
					if (!frm.doc.mobile_no || !frm.doc.user)
						frappe.model.set_value(
							frm.doctype,
							frm.docname,
							"mobile_no",
							data.message.cell_number
						);
				},
			});
		}
	},
});
