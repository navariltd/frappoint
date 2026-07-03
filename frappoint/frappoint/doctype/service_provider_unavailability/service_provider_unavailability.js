// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Provider Unavailability", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
			frm.add_custom_button(
				__("Preview & Reassign"),
				() => show_reassignment_dialog(frm),
				__("Reassignment")
			);
		}
	},
});

function show_reassignment_dialog(frm) {
	frappe.dom.freeze(__("Loading affected appointments..."));
	frappe.call({
		method: "frappoint.frappoint.services.provider_unavailability_service.get_reassignment_preview",
		args: {
			unavailability_name: frm.doc.name,
		},
		callback(r) {
			frappe.dom.unfreeze();
			const preview = r.message || {};
			const appointments = preview.appointments || [];

			if (!appointments.length) {
				frappe.msgprint(__("No active appointments are affected by this unavailability."));
				return;
			}

			render_reassignment_dialog(frm, appointments);
		},
		error() {
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __("Unable to Load Preview"),
				message: __("Failed to load affected appointments. Please try again."),
				indicator: "red",
			});
		},
	});
}

function render_reassignment_dialog(frm, appointments) {
	const dialog = new frappe.ui.Dialog({
		title: __("Reassign Affected Appointments"),
		size: "extra-large",
		fields: [
			{
				fieldname: "summary",
				fieldtype: "HTML",
			},
			{
				fieldname: "appointment_list",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Reassign Appointments"),
		primary_action() {
			const assignments = collect_assignments(dialog, appointments);
			if (!assignments.length) {
				frappe.msgprint(__("No appointments have replacement providers selected."));
				return;
			}

			frappe.confirm(__("Reassign {0} appointment(s)?", [assignments.length]), () => {
				dialog.hide();
				run_reassignment(frm, assignments);
			});
		},
	});

	dialog.fields_dict.summary.$wrapper.html(`
		<div class="text-muted" style="margin-bottom: 12px;">
			${__(
				"Review affected appointments and choose replacement providers. Recommended providers are preselected."
			)}
		</div>
	`);

	dialog.fields_dict.appointment_list.$wrapper.html(build_appointment_list_html(appointments));
	dialog.show();
}

function build_appointment_list_html(appointments) {
	const rows = appointments.map((appointment, appointment_index) => {
		const options = appointment.provider_change_options || [];
		const option_rows = options.length
			? options
					.map((option, option_index) => build_provider_option(option, option_index))
					.join("")
			: `<option value="">${__("No replacement provider available")}</option>`;
		const disabled = options.length ? "" : "disabled";

		return `
			<div class="frappoint-reassignment-row" data-appointment-index="${appointment_index}"
				style="border:1px solid var(--border-color); border-radius:8px; padding:12px; margin-bottom:10px;">
				<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:10px;">
					<div>
						<div style="font-weight:600;">${escape_html(
							appointment.full_name || appointment.customer || appointment.name
						)}</div>
						<div class="text-muted" style="font-size:12px;">
							${escape_html(appointment.appointment_date || "")}
							${escape_html(format_time_range(appointment.start_time, appointment.end_time))}
							${appointment.appointment_type ? ` · ${escape_html(appointment.appointment_type)}` : ""}
						</div>
					</div>
					<a href="/app/service-appointment/${encodeURIComponent(appointment.name)}" target="_blank">
						${escape_html(appointment.name)}
					</a>
				</div>
				<div style="display:grid; grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.2fr); gap:12px; align-items:end;">
					<div>
						<div class="text-muted" style="font-size:12px; margin-bottom:4px;">${__("Current Provider")}</div>
						<div>${escape_html(appointment.current_provider_name || appointment.current_provider || "")}</div>
					</div>
					<div>
						<label class="text-muted" style="font-size:12px; margin-bottom:4px; display:block;">${__(
							"Replacement Provider"
						)}</label>
						<select class="form-control frappoint-replacement-provider" ${disabled}>
							${option_rows}
						</select>
					</div>
				</div>
			</div>
		`;
	});

	return `<div>${rows.join("")}</div>`;
}

function build_provider_option(option, option_index) {
	const provider_name = option.provider_name || option.provider;
	const service_unit_name = option.service_unit_name || option.service_unit || "";
	const label = service_unit_name ? `${provider_name} - ${service_unit_name}` : provider_name;
	const value = JSON.stringify({
		index: option_index,
		provider: option.provider,
		service_unit: option.service_unit || "",
	});
	return `<option value="${escape_html(value)}">${escape_html(label)}</option>`;
}

function collect_assignments(dialog, appointments) {
	const assignments = [];
	dialog.fields_dict.appointment_list.$wrapper
		.find(".frappoint-reassignment-row")
		.each(function () {
			const appointment_index = Number($(this).attr("data-appointment-index"));
			const appointment = appointments[appointment_index];
			const raw_value = $(this).find(".frappoint-replacement-provider").val();
			if (!appointment || !raw_value) return;

			let selected;
			try {
				selected = JSON.parse(raw_value);
			} catch (e) {
				return;
			}

			if (!selected.provider) return;
			assignments.push({
				appointment: appointment.name,
				provider: selected.provider,
				service_unit: selected.service_unit || null,
			});
		});
	return assignments;
}

function run_reassignment(frm, assignments) {
	frappe.dom.freeze(__("Reassigning appointments..."));
	frappe.call({
		method: "frappoint.frappoint.services.provider_unavailability_service.reassign_affected_appointments",
		args: {
			unavailability_name: frm.doc.name,
			assignments: JSON.stringify(assignments),
			auto_assign: 0,
		},
		callback(r) {
			frappe.dom.unfreeze();
			const result = r.message || {};
			const message = __("Reassigned {0} appointment(s). {1} skipped, {2} failed.", [
				result.reassigned_count || 0,
				result.skipped_count || 0,
				result.failed_count || 0,
			]);
			frappe.msgprint({
				title: __("Reassignment Complete"),
				message,
				indicator: result.failed_count ? "orange" : "green",
			});
			frm.reload_doc();
		},
		error() {
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __("Reassignment Failed"),
				message: __("Appointments could not be reassigned. Please try again."),
				indicator: "red",
			});
		},
	});
}

function format_time_range(start_time, end_time) {
	if (!start_time || !end_time) return "";
	return ` · ${String(start_time).split(".")[0]} - ${String(end_time).split(".")[0]}`;
}

function escape_html(value) {
	if (frappe.utils && frappe.utils.escape_html) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
	return String(value ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}
