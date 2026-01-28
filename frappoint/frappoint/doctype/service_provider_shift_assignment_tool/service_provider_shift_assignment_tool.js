// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Provider Shift Assignment Tool", {
	onload(frm) {
		// Set default values
		if (!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("company"));
		}
		if (!frm.doc.action) {
			frm.set_value("action", "Assign Shift");
		}
		if (!frm.doc.status) {
			frm.set_value("status", "Active");
		}
	},
	refresh(frm) {
		frm.disable_save();
		frm.page.clear_primary_action();
		frm.trigger("set_primary_action");
	},

	action(frm) {
		frm.trigger("set_primary_action");
	},

	company(frm) {
		frm.clear_table("providers");
		frm.refresh_field("providers");
	},

	provider_shift_type(frm) {
		frm.trigger("add_fetch_providers_button");
	},

	start_date(frm) {
		// Validate end_date is not before start_date
		if (frm.doc.start_date && frm.doc.end_date && frm.doc.start_date > frm.doc.end_date) {
			frm.set_value("end_date", null);
			frappe.msgprint(__("End Date cannot be before Start Date"));
		}
	},

	end_date(frm) {
		// Validate end_date is not before start_date
		if (frm.doc.start_date && frm.doc.end_date && frm.doc.end_date < frm.doc.start_date) {
			frm.set_value("start_date", null);
			frappe.msgprint(__("Start Date cannot be after End Date"));
		}
	},

	add_fetch_providers_button(frm) {
		frm.add_custom_button(__("Fetch Providers"), () => {
			frm.events.get_providers(frm);
		});
	},

	get_providers(frm) {
		// Only fetch if company is selected
		if (!frm.doc.company) {
			frappe.msgprint(__("Please Select a company"));
			return;
		}

		frm.call({
			method: "get_providers",
			args: {
				advanced_filters: frm.advanced_filters || [],
			},
			doc: frm.doc,
		}).then((r) => {
			if (r.message && r.message.length > 0) {
				frm.events.populate_providers_table(frm, r.message);
			} else {
				frappe.msgprint(__("No eligible providers found based on the selected filters."));
			}
		});
	},

	populate_providers_table(frm, providers) {
		// Clear existing rows
		frm.clear_table("providers");

		// Add fetched providers to the table
		providers.forEach((provider) => {
			let row = frm.add_child("providers");
			row.service_provider = provider.service_provider;
			row.service_provider_name = provider.provider_name;
			row.service_unit = provider.service_unit;
		});

		frm.refresh_field("providers");

		frappe.show_alert({
			message: __("{0} provider(s) added to the table", [providers.length]),
			indicator: "green",
		});
	},

	set_primary_action(frm) {
		frm.page.clear_primary_action();

		frm.page.set_primary_action(__("Assign Shifts"), () => {
			frm.events.validate_and_assign(frm);
		});
	},

	validate_and_assign(frm) {
		// Validation
		if (!frm.doc.company) {
			frappe.msgprint(__("Please select a Company"));
			return;
		}

		if (!frm.doc.provider_shift_type) {
			frappe.msgprint(__("Please select a Service Provider Shift Type"));
			return;
		}

		if (!frm.doc.start_date) {
			frappe.msgprint(__("Please select a Start Date"));
			return;
		}

		if (!frm.doc.status) {
			frappe.msgprint(__("Please select a Status to set"));
			return;
		}

		if (!frm.doc.providers || frm.doc.providers.length === 0) {
			frappe.msgprint(__("Please add at least one Service Provider to the table"));
			return;
		}

		const provider_names = frm.doc.providers.map((p) => p.service_provider).join(", ");

		// Show confirmation dialog
		frappe.confirm(
			__("Assign <b>{0}</b> status to {1} Service Provider(s)?", [
				frm.doc.status,
				frm.doc.providers.length,
			]),
			() => {
				frm.events.call_bulk_assign(frm);
			}
		);
	},

	call_bulk_assign(frm) {
		frm.call({
			method: "bulk_assign_shifts",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Assigning Shifts..."),
		}).then((r) => {
			if (r.message) {
				frm.events.show_assignment_results(frm, r.message);
			}
		});
	},

	show_assignment_results(frm, result) {
		const success_count = result.success ? result.success.length : 0;
		const failure_count = result.failure ? result.failure.length : 0;

		// Build success message
		let message = `<div class="assignment-results">`;

		if (success_count > 0) {
			message += `<div class="result-section success">
				<h6 class="text-success">${__("Successful")}: ${success_count}</h6>
				<ul>`;
			result.success.forEach((item) => {
				message += `<li>${item.provider}</li>`;
			});
			message += `</ul></div>`;
		}

		if (failure_count > 0) {
			message += `<div class="result-section failure">
				<h6 class="text-danger">${__("Failed")}: ${failure_count}</h6>
				<ul>`;
			result.failure.forEach((item) => {
				message += `<li>${item.provider} - ${item.error || "Unknown error"}</li>`;
			});
			message += `</ul></div>`;
		}

		message += `</div>`;

		// Show results in a dialog
		frappe.msgprint({
			title: __("Assignment Results"),
			message: message,
			indicator: failure_count > 0 ? "yellow" : "green",
		});

		// Clear the table after successful assignment
		if (success_count > 0) {
			frm.clear_table("providers");
			frm.refresh_field("providers");
		}
	},
});
