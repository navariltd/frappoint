# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt


import datetime
import json

import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, get_link_to_form, get_time, getdate, now_datetime


class MaximumCapacityError(frappe.ValidationError):
	pass


class OverlapError(frappe.ValidationError):
	pass


class ServiceAppointment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_video_conferencing: DF.Check
		amended_from: DF.Link | None
		appointment_date: DF.Date
		appointment_provider: DF.Link
		appointment_type: DF.Link
		company: DF.Link
		confirmation_token: DF.Data | None
		customer: DF.Link | None
		details: DF.SmallText | None
		duration: DF.Int
		email: DF.Data | None
		end_time: DF.Time
		event: DF.Link | None
		full_name: DF.Data
		google_meet_link: DF.Data | None
		mobile_no: DF.Data
		mode_of_payment: DF.Link | None
		naming_series: DF.Literal["SVC-APP-.MM.-.YY.-.###."]
		notes: DF.Text | None
		payment_status: DF.Literal["Unpaid", "Paid", "Refunded", "Cancellation"]
		scheduled_time: DF.Datetime
		source: DF.Literal["Desk", "Portal"]
		start_time: DF.Time
		status: DF.Literal["Open", "Confirmed", "Rescheduled", "Completed", "Cancelled", "Closed", "No Show"]
		total_amount: DF.Currency
	# end: auto-generated types
	pass

	def validate(self):
		self.validate_appointment_date_and_times()
		self.validate_overlaps()
		self.validate_customer_overlap()

	def after_insert(self):
		self.insert_calendar_event()

	def validate_appointment_date_and_times(self):
		start_dt = get_datetime(f"{self.appointment_date} {self.start_time}")
		end_dt = get_datetime(f"{self.appointment_date} {self.end_time}")

		if start_dt >= end_dt:
			frappe.throw(_("End Time must be after Start Time"))

		if start_dt < now_datetime():
			frappe.throw(_("You cannot schedule an appointment in the past"))

	def validate_overlaps(self):
		"""
		Validate that the appointment does not overlap with existing appointments
		for the same provider on the same date and time range.
		"""
		if not self.appointment_provider:
			return

		if not self.appointment_date or not self.start_time or not self.end_time:
			return

		# The overlap logic checks three conditions:
		# 1. Existing appointment starts before and ends during this appointment
		# 2. Existing appointment starts during this appointment
		# 3. Existing appointment has exact same start time
		overlapping_appointments = frappe.db.sql(
			"""
			SELECT
				name, appointment_provider, full_name, start_time, end_time, status
			FROM
				`tabService Appointment`
			WHERE
				appointment_date = %(appointment_date)s
				AND name != %(name)s
				AND status NOT IN ('Cancelled', 'No Show', 'Closed')
				AND docstatus != 2
				AND appointment_provider = %(appointment_provider)s
				AND start_time IS NOT NULL
				AND end_time IS NOT NULL
				AND (
					(start_time < %(start_time)s AND end_time > %(start_time)s) OR
					(start_time >= %(start_time)s AND start_time < %(end_time)s) OR
					(start_time = %(start_time)s)
				)
			""",
			{
				"appointment_date": self.appointment_date,
				"name": self.name or "new",
				"appointment_provider": self.appointment_provider,
				"start_time": self.start_time,
				"end_time": self.end_time,
			},
			as_dict=True,
		)

		if overlapping_appointments:
			overlap_details = "<br>".join(
				[
					f"• <b>{get_link_to_form(self.doctype, appt['name'])}</b>: {appt['start_time']} - {appt['end_time']} "
					f"({appt['full_name']}) - Status: {appt['status']}"
					for appt in overlapping_appointments
				]
			)

			frappe.throw(
				_("Appointment for {0} on {1} overlaps with existing appointment(s):<br><br>{2}").format(
					frappe.bold(self.appointment_provider),
					frappe.bold(frappe.format(self.appointment_date, {"fieldtype": "Date"})),
					overlap_details,
				),
				OverlapError,
				title=_("Overlapping Appointment"),
			)

	def validate_customer_overlap(self):
		"""
		Validate that the customer doesn't have multiple appointments at the same time.
		Called to prevent customers from double-booking.
		"""
		if not self.customer:
			return

		if not self.appointment_date or not self.start_time or not self.end_time:
			return

		overlapping_customer_appointments = frappe.db.sql(
			"""
			SELECT
				name, appointment_provider, start_time, end_time, status
			FROM
				`tabService Appointment`
			WHERE
				appointment_date = %(appointment_date)s
				AND name != %(name)s
				AND status NOT IN ('Cancelled', 'No Show', 'Closed')
				AND docstatus != 2
				AND customer = %(customer)s
				AND start_time IS NOT NULL
				AND end_time IS NOT NULL
				AND (
					(start_time < %(start_time)s AND end_time > %(start_time)s) OR
					(start_time >= %(start_time)s AND start_time < %(end_time)s) OR
					(start_time = %(start_time)s)
				)
			""",
			{
				"appointment_date": self.appointment_date,
				"name": self.name or "new",
				"customer": self.customer,
				"start_time": self.start_time,
				"end_time": self.end_time,
			},
			as_dict=True,
		)

		if overlapping_customer_appointments:
			frappe.msgprint(
				_("Customer {0} has another appointment at the same time: {1}").format(
					frappe.bold(self.customer),
					", ".join([appt["name"] for appt in overlapping_customer_appointments]),
				),
				indicator="orange",
				alert=True,
			)

	def insert_calendar_event(self):
		if not self.appointment_provider:
			return

		starts_on = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.start_time))
		ends_on = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.end_time))

		google_calendar = frappe.db.get_value(
			"Appointment Provider", self.appointment_provider, "google_calendar"
		)
		if not google_calendar:
			google_calendar = frappe.db.get_single_value(
				"Service Appointment Settings", "default_google_calendar"
			)

		color = frappe.db.get_value("Appointment Provider", self.appointment_provider, "color_code")
		if not color:
			color = ""

		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"{self.name} - {self.company}",
				"event_type": "Private",
				"color": color,
				"send_reminder": 1,
				"starts_on": starts_on,
				"ends_on": ends_on,
				"status": "Open",
				"all_day": 0,
				"sync_with_google_calendar": 1 if google_calendar else 0,
				"add_video_conferencing": 1 if self.add_video_conferencing and google_calendar else 0,
				"google_calendar": google_calendar,
				"description": f"{self.name} - {self.company}",
				"pulled_from_google_calendar": 0,
			}
		)
		participants = []

		participants.append(
			{"reference_doctype": "Appointment Provider", "reference_docname": self.appointment_provider}
		)
		participants.append({"reference_doctype": "Customer", "reference_docname": self.customer})

		event.update({"event_participants": participants})

		event.insert(ignore_permissions=True)

		event.reload()
		if self.add_video_conferencing and not event.google_meet_link:
			frappe.msgprint(
				_("Could not add conferencing to this Appointment, please contact System Manager"),
				indicator="error",
				alert=True,
			)

		self.db_set({"event": event.name, "google_meet_link": event.google_meet_link})
		self.notify_update()

	def send_confirmation_msg(self):
		if frappe.db.get_single_value("Service Appointment Settings", "appointment_confirmation"):
			message = frappe.db.get_single_value(
				"Service Appointment Settings", "appointment_confirmation_msg"
			)

			try:
				self.send_message(message)
			except Exception:
				frappe.log_error(frappe.get_traceback(), _("Appointment Confirmation Message Not Sent"))
				frappe.msgprint(_("Appointment Confirmation Message Not Sent"), indicator="orange")

	@staticmethod
	def send_message(self, message):
		context = {"doc": self, "alert": self, "comments": None}
		if self.get("_comments"):
			context["comments"] = json.loads(self.get("_comments"))

		# jinja to string convertion happens here
		message = frappe.render_template(message, context)
		number = [self.mobile_no]
		try:
			send_sms(number, message)
		except Exception:
			frappe.msgprint(_("SMS not sent, please check SMS Settings"), alert=True)
