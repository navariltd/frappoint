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
