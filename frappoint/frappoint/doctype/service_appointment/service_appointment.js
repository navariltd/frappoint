// Copyright (c) 2025, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Appointment", {
	refresh(frm) {},

	start_time(frm) {
		calculate_end_time(frm);
		validate_appointment_times(frm);
	},

	end_time(frm) {
		validate_appointment_times(frm);
	},

	appointment_date(frm) {
		calculate_end_time(frm);
		validate_appointment_times(frm);
	},

	appointment_type(frm) {
		calculate_end_time(frm);

		if (frm.doc.appointment_type) {
			frm.add_custom_button(__("Show Available Slots"), function () {
				show_slot_picker(frm);
			});
		}
	},

	before_save(frm) {
		if (
			frm.doc.selected_slot_ids &&
			frm.doc.appointment_provider &&
			frm.doc.appointment_date &&
			frm.doc.start_time
		) {
			frm.doc.__booking_required = true;
		}
	},
});

// Helper: Convert date + time strings into a JS Date object
function parse_time_to_datetime(date_str, time_str) {
	if (!time_str) return null;
	let time_parts = time_str.split(":");
	if (time_parts.length < 2) return null;

	const year = date_str.split("-")[0];
	const month = parseInt(date_str.split("-")[1], 10) - 1;
	const day = date_str.split("-")[2];
	const hours = parseInt(time_parts[0], 10);
	const minutes = parseInt(time_parts[1], 10);

	return new Date(year, month, day, hours, minutes, 0);
}

function calculate_end_time(frm) {
	const start_time = frm.doc.start_time;
	const appointment_date = frm.doc.appointment_date;

	let duration = frm.doc.duration;
	if (!start_time || !appointment_date || duration <= 0) return;

	let start_dt = parse_time_to_datetime(appointment_date, start_time);
	if (!start_dt) return;

	start_dt.setMinutes(start_dt.getMinutes() + duration);

	const end_hours = start_dt.getHours().toString().padStart(2, "0");
	const end_minutes = start_dt.getMinutes().toString().padStart(2, "0");

	frm.set_value("end_time", `${end_hours}:${end_minutes}`);
}

function validate_appointment_times(frm) {
	const start_time = frm.doc.start_time;
	const end_time = frm.doc.end_time;
	const appointment_date = frm.doc.appointment_date;

	if (!start_time || !end_time || !appointment_date) return;

	const start_dt = parse_time_to_datetime(appointment_date, start_time);
	const end_dt = parse_time_to_datetime(appointment_date, end_time);
	const now = new Date();

	if (!start_dt || !end_dt) return;

	if (start_dt >= end_dt) {
		frappe.msgprint(__("End Time must be after Start Time"));
		return;
	}

	if (start_dt < now) {
		frappe.msgprint(__("You cannot schedule an appointment in the past"));
		return;
	}
}

function load_available_slots(frm) {
	if (!frm.doc.appointment_type) {
		return Promise.reject("No appointment type selected");
	}

	return new Promise((resolve, reject) => {
		frappe.call({
			method: "frappoint.frappoint.doctype.service_appointment.service_appointment.get_appointment_slots",
			args: {
				appointment_type: frm.doc.appointment_type,
				provider: frm.doc.appointment_provider || null,
				date: frm.doc.appointment_date || null,
			},
			callback: function (r) {
				if (r.message) {
					frm.available_slots = r.message;
					resolve(r.message);
				} else {
					reject("No slots available");
				}
			},
			error: function (err) {
				reject(err);
			},
		});
	});
}

function show_slot_picker(frm) {
	frappe.show_alert({
		message: __("Loading available slots..."),
		indicator: "blue",
	});

	load_available_slots(frm)
		.then((slots) => {
			if (!slots || slots.length === 0) {
				frappe.msgprint(
					__("No available slots found. Please adjust your search criteria.")
				);
				return;
			}

			// Create dialog to show available slots
			let d = new frappe.ui.Dialog({
				title: __("Select Appointment Slot"),
				fields: [
					{
						fieldname: "provider_filter",
						fieldtype: "Link",
						label: __("Provider"),
						options: "Appointment Provider",
						get_query: function () {
							return {
								filters: {
									name: ["in", frm.available_slots.map((s) => s.provider)],
								},
							};
						},
						onchange: function () {
							update_slot_display(d, frm);
						},
					},
					{
						fieldname: "slot_display",
						fieldtype: "HTML",
					},
				],
				primary_action_label: __("Book Selected Slot"),
				primary_action: function (values) {
					let selected_slot = d.selected_slot;
					if (!selected_slot) {
						frappe.msgprint(__("Please select a slot"));
						return;
					}

					select_slot(frm, selected_slot, d);
				},
			});

			update_slot_display(d, frm);
			d.show();
		})
		.catch((err) => {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to load available slots. Please try again."),
				indicator: "red",
			});
			console.error("Error loading slots:", err);
		});
}

function select_slot(frm, slot_data, dialog) {
	frm.set_value("appointment_provider", slot_data.provider);
	frm.set_value("appointment_date", slot_data.date);
	frm.set_value("start_time", slot_data.start_time);
	frm.set_value("end_time", slot_data.end_time);

	frm.set_value("selected_slot_ids", JSON.stringify(slot_data.slot_ids));

	frappe.show_alert({
		message: __("Slot selected. Please save the appointment to confirm booking."),
		indicator: "green",
	});

	dialog.hide();
}

function update_slot_display(dialog, frm) {
	let provider_filter = dialog.get_value("provider_filter");
	let slots = frm.available_slots;

	if (provider_filter) {
		slots = slots.filter((s) => s.provider === provider_filter);
	}

	let html = '<div class="slot-picker">';

	slots.forEach((provider_data) => {
		html += `<div class="provider-section">
			<h4>${provider_data.provider_name}</h4>`;

		provider_data.available_dates.forEach((date_data) => {
			html += `<div class="date-section">
				<h5>${frappe.datetime.str_to_user(date_data.date)}</h5>
				<div class="slot-grid">`;

			date_data.slots.forEach((slot) => {
				let slot_id = `${provider_data.provider}_${date_data.date}_${slot.start_time}`;
				html += `<button class="btn btn-default btn-sm slot-btn"
					data-provider="${provider_data.provider}"
					data-provider-name="${provider_data.provider_name}"
					data-date="${date_data.date}"
					data-start="${slot.start_time}"
					data-end="${slot.end_time}"
					data-slots='${JSON.stringify(slot.slot_ids)}'
					onclick="selectSlot(this)">
					${slot.start_time} - ${slot.end_time}
				</button>`;
			});

			html += "</div></div>";
		});

		html += "</div>";
	});

	html += "</div>";

	html += `<style>
		.slot-picker { padding: 15px; }
		.provider-section { margin-bottom: 20px; }
		.date-section { margin-bottom: 15px; }
		.slot-grid { display: flex; flex-wrap: wrap; gap: 10px; }
		.slot-btn { min-width: 150px; }
		.slot-btn.selected { background-color: #5e64ff; color: white; }
	</style>`;

	dialog.fields_dict.slot_display.$wrapper.html(html);
}

// Global function to handle slot selection
window.selectSlot = function (btn) {
	// Remove previous selection
	document.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));

	btn.classList.add("selected");

	let dialog = cur_dialog;
	dialog.selected_slot = {
		provider: btn.dataset.provider,
		provider_name: btn.dataset.providerName,
		date: btn.dataset.date,
		start_time: btn.dataset.start,
		end_time: btn.dataset.end,
		slot_ids: JSON.parse(btn.dataset.slots),
	};
};
