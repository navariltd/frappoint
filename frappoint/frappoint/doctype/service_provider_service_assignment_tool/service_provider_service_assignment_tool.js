// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Provider Service Assignment Tool", {
	refresh(frm) {
		frm.disable_save();
		frm.page.clear_primary_action();
		frm.trigger("set_primary_action");
		frm.trigger("add_fetch_button");
	},

	action(frm) {
		frm.trigger("set_primary_action");
		frm.trigger("add_fetch_button");
		frm.trigger("clear_tables");
	},

	company(frm) {
		frm.trigger("clear_tables");
	},

	service_type(frm) {
		frm.trigger("clear_tables");
	},

	service_provider(frm) {
		frm.trigger("clear_tables");
	},

	status(frm) {
		frm.trigger("clear_tables");
	},

	branch(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	department(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	designation(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	grade(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	service_unit(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	service_unit_type(frm) {
		if (frm.doc.action === "Assign Service to Providers") {
			frm.trigger("clear_tables");
		}
	},

	clear_tables(frm) {
		frm.clear_table("providers");
		frm.clear_table("services");
		frm.refresh_field("providers");
		frm.refresh_field("services");
	},

	set_primary_action(frm) {
		frm.page.clear_primary_action();
		frm.page.set_primary_action(__("Assign Services"), () => {
			frm.events.validate_and_assign(frm);
		});
	},

	add_fetch_button(frm) {
		frm.clear_custom_buttons();

		if (frm.doc.action === "Assign Service to Providers") {
			frm.add_custom_button(__("Fetch Providers"), () => {
				frm.events.get_providers(frm);
			});
		} else if (frm.doc.action === "Assign Services to Provider") {
			frm.add_custom_button(__("Fetch Services"), () => {
				frm.events.get_services(frm);
			});
		}
	},

	get_providers(frm) {
		if (!frm.doc.company) {
			frappe.msgprint(__("Please select a Company"));
			return;
		}

		if (!frm.doc.service_type) {
			frappe.msgprint(__("Please select a Service Type"));
			return;
		}

		frm.call({
			method: "get_providers",
			doc: frm.doc,
		}).then((r) => {
			if (r.message && r.message.length > 0) {
				frm.events.populate_providers_table(frm, r.message);
			} else {
				frappe.msgprint(__("No eligible providers found based on the selected filters."));
			}
		});
	},

	get_services(frm) {
		if (!frm.doc.company) {
			frappe.msgprint(__("Please select a Company"));
			return;
		}

		if (!frm.doc.service_provider) {
			frappe.msgprint(__("Please select a Service Provider"));
			return;
		}

		frm.call({
			method: "get_services",
			doc: frm.doc,
		}).then((r) => {
			if (r.message && r.message.length > 0) {
				frm.events.populate_services_table(frm, r.message);
			} else {
				frappe.msgprint(__("No eligible services found."));
			}
		});
	},

	populate_providers_table(frm, providers) {
		frm.clear_table("providers");

		providers.forEach((provider) => {
			let row = frm.add_child("providers");
			row.service_provider = provider.service_provider;
			row.provider_name = provider.provider_name;
			row.service_unit = provider.service_unit;
		});

		frm.refresh_field("providers");

		frappe.show_alert({
			message: __("{0} provider(s) added to the table", [providers.length]),
			indicator: "green",
		});
	},

	populate_services_table(frm, services) {
		frm.clear_table("services");

		services.forEach((service) => {
			let row = frm.add_child("services");
			row.service_type = service.service_type;
			row.service_type_name = service.service_type_name;
		});

		frm.refresh_field("services");

		frappe.show_alert({
			message: __("{0} service(s) added to the table", [services.length]),
			indicator: "green",
		});
	},

	validate_and_assign(frm) {
		if (!frm.doc.company) {
			frappe.msgprint(__("Please select a Company"));
			return;
		}

		if (frm.doc.action === "Assign Service to Providers") {
			if (!frm.doc.service_type) {
				frappe.msgprint(__("Please select a Service Type"));
				return;
			}

			if (!frm.doc.providers || frm.doc.providers.length === 0) {
				frappe.msgprint(__("Please add at least one Service Provider to the table"));
				return;
			}

			frappe.confirm(
				__("Assign <b>{0}</b> to {1} provider(s)?", [
					frm.doc.service_type,
					frm.doc.providers.length,
				]),
				() => {
					frm.events.call_bulk_assign(frm);
				}
			);
		} else if (frm.doc.action === "Assign Services to Provider") {
			if (!frm.doc.service_provider) {
				frappe.msgprint(__("Please select a Service Provider"));
				return;
			}

			if (!frm.doc.services || frm.doc.services.length === 0) {
				frappe.msgprint(__("Please add at least one Service Type to the table"));
				return;
			}

			frappe.confirm(
				__("Assign {0} service(s) to <b>{1}</b>?", [
					frm.doc.services.length,
					frm.doc.service_provider,
				]),
				() => {
					frm.events.call_bulk_assign(frm);
				}
			);
		}
	},

	call_bulk_assign(frm) {
		frm.call({
			method: "bulk_assign_services",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Assigning Services..."),
		}).then((r) => {
			if (r.message) {
				frm.events.show_assignment_results(frm, r.message);
			}
		});
	},

	show_assignment_results(frm, result) {
		const success_count = result.success ? result.success.length : 0;
		const failure_count = result.failure ? result.failure.length : 0;

		let message = `<div class="assignment-results">`;

		if (success_count > 0) {
			message += `<div class="result-section success">
				<h6 class="text-success">${__("Successful")}: ${success_count}</h6>
				<ul>`;
			result.success.forEach((item) => {
				const label = item.provider || item.service_type;
				const action = item.action || "processed";
				message += `<li>${label} - ${action}</li>`;
			});
			message += `</ul></div>`;
		}

		if (failure_count > 0) {
			message += `<div class="result-section failure">
				<h6 class="text-danger">${__("Failed")}: ${failure_count}</h6>
				<ul>`;
			result.failure.forEach((item) => {
				const label = item.provider || item.service;
				message += `<li>${label} - ${item.error || "Unknown error"}</li>`;
			});
			message += `</ul></div>`;
		}

		message += `</div>`;

		frappe.msgprint({
			title: __("Assignment Results"),
			message: message,
			indicator: failure_count > 0 ? "yellow" : "green",
		});

		// Clear tables after successful assignment
		if (success_count > 0) {
			frm.clear_table("providers");
			frm.clear_table("services");
			frm.refresh_field("providers");
			frm.refresh_field("services");
		}
	},
});
