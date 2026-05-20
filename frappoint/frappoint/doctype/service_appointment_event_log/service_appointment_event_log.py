# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds

WORK_SESSION_TYPES = {"Start", "Resume"}
POINT_IN_TIME_TYPES = {"Check-in", "End"}


class ServiceAppointmentEventLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		appointment: DF.Link
		booking: DF.Link | None
		created_by: DF.Link | None
		duration_seconds: DF.Int
		end_time: DF.Datetime | None
		log_type: DF.Literal["Check-in", "Start", "Pause", "Resume", "End"]
		notes: DF.Text | None
		start_time: DF.Datetime
	# end: auto-generated types

	def validate(self):
		self.created_by = self.created_by or frappe.session.user
		if self.end_time and get_datetime(self.end_time) < get_datetime(self.start_time):
			frappe.throw(_("End time cannot be before start time."))
		if self.end_time:
			self.duration_seconds = max(0, int(time_diff_in_seconds(self.end_time, self.start_time)))
		elif self.log_type in POINT_IN_TIME_TYPES:
			self.duration_seconds = 0


def _normalize_action(action: str) -> str:
	return (action or "").strip().lower()


def _serialize_log(log):
	start_dt = get_datetime(log.start_time) if log.start_time else None
	end_dt = get_datetime(log.end_time) if log.end_time else None
	duration_seconds = int(log.duration_seconds or 0)
	if not duration_seconds and start_dt and end_dt:
		duration_seconds = max(0, int(time_diff_in_seconds(end_dt, start_dt)))

	return {
		"name": log.name,
		"appointment": log.appointment,
		"booking": log.booking,
		"logType": log.log_type,
		"startTime": log.start_time,
		"endTime": log.end_time,
		"durationSeconds": duration_seconds,
		"createdBy": log.created_by,
		"notes": log.notes,
	}


def get_appointment_event_logs(appointment_name: str) -> list[dict]:
	rows = frappe.get_all(
		"Service Appointment Event Log",
		filters={"appointment": appointment_name},
		fields=[
			"name",
			"appointment",
			"booking",
			"log_type",
			"start_time",
			"end_time",
			"duration_seconds",
			"created_by",
			"notes",
		],
		order_by="start_time asc, creation asc",
	)
	return [_serialize_log(row) for row in rows]


def compute_appointment_time_summary(logs: list[dict], now_dt=None) -> dict:
	now_dt = get_datetime(now_dt) if now_dt else now_datetime()
	effective_duration_seconds = 0
	total_pause_seconds = 0
	pause_segments = []
	active_session = None

	for log in logs:
		start_dt = get_datetime(log.get("startTime")) if log.get("startTime") else None
		end_dt = get_datetime(log.get("endTime")) if log.get("endTime") else None
		log_type = log.get("logType")

		if not start_dt:
			continue

		duration_seconds = int(log.get("durationSeconds") or 0)
		if not duration_seconds and end_dt:
			duration_seconds = max(0, int(time_diff_in_seconds(end_dt, start_dt)))

		if log_type in WORK_SESSION_TYPES:
			if end_dt:
				effective_duration_seconds += duration_seconds
			else:
				active_session = {
					**log,
					"sessionType": "work",
					"elapsedSeconds": max(0, int(time_diff_in_seconds(now_dt, start_dt))),
				}
				effective_duration_seconds += active_session["elapsedSeconds"]

		if log_type == "Pause":
			pause_duration = duration_seconds
			if not end_dt:
				pause_duration = max(0, int(time_diff_in_seconds(now_dt, start_dt)))
				active_session = {
					**log,
					"sessionType": "pause",
					"elapsedSeconds": pause_duration,
				}
			total_pause_seconds += pause_duration
			pause_segments.append({**log, "durationSeconds": pause_duration})

	return {
		"effectiveDurationSeconds": effective_duration_seconds,
		"totalPauseSeconds": total_pause_seconds,
		"pauseSegments": pause_segments,
		"activeSession": active_session,
		"isPaused": bool(active_session and active_session.get("sessionType") == "pause"),
		"isRunning": bool(active_session and active_session.get("sessionType") == "work"),
	}


def _get_open_log(appointment_name: str, log_types: set[str]):
	rows = frappe.get_all(
		"Service Appointment Event Log",
		filters={
			"appointment": appointment_name,
			"log_type": ["in", list(log_types)],
			"end_time": ["is", "not set"],
		},
		fields=["name", "appointment", "booking", "log_type", "start_time", "end_time", "duration_seconds"],
		order_by="start_time desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def _close_log(log_name: str, end_time):
	log = frappe.get_doc("Service Appointment Event Log", log_name)
	log.end_time = end_time
	log.duration_seconds = max(0, int(time_diff_in_seconds(end_time, log.start_time)))
	log.save(ignore_permissions=True)
	return log


def _create_log(appointment, log_type: str, event_time, notes: str | None = None, end_time=None):
	log = frappe.get_doc(
		{
			"doctype": "Service Appointment Event Log",
			"appointment": appointment.name,
			"booking": appointment.booking_id,
			"log_type": log_type,
			"start_time": event_time,
			"end_time": end_time,
			"duration_seconds": 0,
			"created_by": frappe.session.user,
			"notes": notes,
		}
	)
	if end_time:
		log.duration_seconds = max(0, int(time_diff_in_seconds(end_time, event_time)))
	log.insert(ignore_permissions=True)
	return log


def apply_appointment_event_action(appointment, action: str, notes: str | None = None, action_time=None):
	action = _normalize_action(action)
	event_time = get_datetime(action_time) if action_time else now_datetime()
	open_work_log = _get_open_log(appointment.name, WORK_SESSION_TYPES)
	open_pause_log = _get_open_log(appointment.name, {"Pause"})

	if action == "check_in":
		_create_log(appointment, "Check-in", event_time, notes=notes, end_time=event_time)
		if not appointment.checked_in_at:
			appointment.checked_in_at = event_time
		if appointment.status not in [
			"Cancelled",
			"Closed",
			"Completed",
			"No Show",
			"Checked In",
			"In Progress",
		]:
			appointment.status = "Checked In"
		appointment.save(ignore_permissions=True)
		frappe.db.commit()
		return {"logType": "Check-in", "timestamp": event_time}

	if action == "start":
		if open_work_log:
			frappe.throw(_("Only one active work session is allowed at a time."))
		if open_pause_log:
			frappe.throw(_("Resume the paused session before starting a new one."))
		_create_log(appointment, "Start", event_time, notes=notes)
		if not appointment.actual_start_time:
			appointment.actual_start_time = get_datetime(event_time).time()
		if appointment.status not in ["Cancelled", "Closed", "Completed", "No Show"]:
			appointment.status = "In Progress"
		appointment.save(ignore_permissions=True)
		frappe.db.commit()
		return {"logType": "Start", "timestamp": event_time}

	if action == "pause":
		if open_pause_log:
			frappe.throw(_("Appointment is already paused."))
		if not open_work_log:
			frappe.throw(_("There is no active running session to pause."))
		_close_log(open_work_log.name, event_time)
		_create_log(appointment, "Pause", event_time, notes=notes)
		return {"logType": "Pause", "timestamp": event_time}

	if action == "resume":
		if not open_pause_log:
			frappe.throw(_("Resume must follow an active pause."))
		if open_work_log:
			frappe.throw(_("Cannot resume while another work session is active."))
		_close_log(open_pause_log.name, event_time)
		_create_log(appointment, "Resume", event_time, notes=notes)
		return {"logType": "Resume", "timestamp": event_time}

	if action in {"complete", "end"}:
		if open_pause_log:
			_close_log(open_pause_log.name, event_time)
		if open_work_log:
			_close_log(open_work_log.name, event_time)
		_create_log(appointment, "End", event_time, notes=notes, end_time=event_time)
		appointment.actual_end_time = get_datetime(event_time).time()
		# Compute actual_duration from event logs
		logs = get_appointment_event_logs(appointment.name)
		time_summary = compute_appointment_time_summary(logs, now_dt=event_time)
		effective_seconds = time_summary.get("effectiveDurationSeconds", 0)
		appointment.actual_duration = max(1, effective_seconds // 60)  # Convert to minutes, minimum 1
		appointment.status = "Completed"
		appointment.save(ignore_permissions=True)
		frappe.db.commit()
		return {"logType": "End", "timestamp": event_time}

	frappe.throw(_("Unsupported appointment timing action: {0}").format(action))
