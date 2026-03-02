# Copyright (c) 2025, Navari LTD and contributors
# For license information, please see license.txt


import datetime
import json

import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.desk.calendar import get_event_conditions
from frappe.desk.reportview import build_match_conditions
from frappe.model.document import Document
from frappe.utils import (
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	now_datetime,
	today,
)

from ..service_provider_appointment_slot.service_provider_appointment_slot import (
	check_provider_slot_capacity,
	check_service_unit_capacity,
	service_type_requires_service_unit,
)


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

		from frappoint.frappoint.doctype.service_appointment_guest.service_appointment_guest import (
			ServiceAppointmentGuest,
		)
		from frappoint.frappoint.doctype.service_appointment_lost_reason_detail.service_appointment_lost_reason_detail import (
			ServiceAppointmentLostReasonDetail,
		)

		actual_duration: DF.Int
		actual_end_time: DF.Time | None
		actual_start_time: DF.Time | None
		add_video_conferencing: DF.Check
		amended_from: DF.Link | None
		appointment_date: DF.Date
		appointment_price: DF.Data
		appointment_provider: DF.Link
		appointment_type: DF.Link
		cancellation_date: DF.Datetime | None
		cancellation_notes: DF.Text | None
		cancellation_reasons: DF.TableMultiSelect[ServiceAppointmentLostReasonDetail]
		company: DF.Link
		confirmation_token: DF.Data | None
		coupon_code: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		details: DF.SmallText | None
		discount_amount: DF.Currency
		duration: DF.Int
		email: DF.Data | None
		end_time: DF.Time
		event: DF.Link | None
		full_name: DF.Data
		google_meet_link: DF.Data | None
		grand_total: DF.Currency
		guests: DF.Table[ServiceAppointmentGuest]
		is_guest: DF.Check
		mobile_no: DF.Data
		mode_of_payment: DF.Link | None
		naming_series: DF.Literal["SVC-APP-.MM.-.YY.-.###."]
		notes: DF.Text | None
		payment_status: DF.Literal["Unpaid", "Paid", "Refunded", "Cancellation"]
		reschedule_date: DF.Datetime | None
		reschedule_notes: DF.Text | None
		reschedule_reasons: DF.TableMultiSelect[ServiceAppointmentLostReasonDetail]
		rescheduled_from: DF.Data | None
		rescheduled_to: DF.Data | None
		scheduled_time: DF.Datetime
		selected_slot_ids: DF.SmallText | None
		service_unit: DF.Link | None
		source: DF.Literal["Desk", "Portal"]
		start_time: DF.Time
		status: DF.Literal["Open", "Confirmed", "Rescheduled", "Completed", "Cancelled", "Closed", "No Show"]
		total_amount: DF.Currency
		total_guests: DF.Int
	# end: auto-generated types

	def validate(self):
		self.validate_appointment_date_and_times()
		self.validate_guest_requirements()
		self.validate_overlaps()
		self.validate_appointment_capacity()
		self.validate_price_and_currency()

		if self.appointment_type and not self.company:
			self.company = self.set_company_from_type()

		if self.appointment_type and not self.duration:
			self.set_duration_from_type()

		if self.status == "Confirmed":
			self.validate_required_for_billing()

	def after_insert(self):
		self.insert_calendar_event()

	def before_save(self):
		"""Book slots before saving if slot selection was made"""

		self.assign_service_unit_to_appointment()
		self.validate_service_unit_requirement()

		if self.selected_slot_ids and self.appointment_provider and self.appointment_date and self.start_time:
			# For new bookings or when slots have changed, book the new slots
			if self.is_new() or not self._slots_already_booked():
				self.book_selected_slots()
			# If slots already booked but selection changed, release and rebook
			elif self._slots_already_booked():
				old_doc = self.get_doc_before_save()
				if old_doc and old_doc.selected_slot_ids != self.selected_slot_ids:
					self.release_slots()
					self.book_selected_slots()

		if self.coupon_code:
			self.apply_coupon_if_any()
			self.calculate_grand_total()

	def on_submit(self):
		"""Confirm appointment"""
		if not self.appointment_price:
			frappe.throw("Please select a price for this appointment")

		if self.status != "Confirmed":
			self.db_set("status", "Confirmed")

		if self.coupon_code:
			coupon = frappe.get_doc("Service Appointment Coupon Code", self.coupon_code)
			coupon.db_set("times_used", coupon.get_usage_count())

	def on_cancel(self):
		"""Release slots when appointment is cancelled"""
		self.handle_cancellation()

	def on_update(self):
		"""Handle appointment confirmations"""
		if self.has_value_changed("status"):
			self.handle_status_change()

	def on_update_after_submit(self):
		"""Handle status changes and reschedules and cancellations"""
		# Validate actual end time when completing appointment
		if self.has_value_changed("status") and self.status == "Completed":
			if not self.actual_end_time:
				frappe.throw(
					_("Actual End Time is required to mark appointment as Completed"),
					title=_("Actual End Time Required"),
				)

			self.calculate_actual_duration()

		if self.has_value_changed("status"):
			self.handle_status_change()

	def on_trash(self):
		"""Release slots when appointment is deleted and prevent deletion if billing exists"""
		self.check_linked_documents_before_delete()
		self.delete_linked_event()
		self.release_slots()

	def on_payment_authorized(self, payment_status):
		if payment_status in ["Authorized", "Completed"]:
			# confirm the appointment
			self.update_payment_record()

	def update_payment_record(self):
		request = frappe.get_all(
			"Integration Request",
			{
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
				# "owner": frappe.session.user,
			},
			order_by="creation desc",
			limit=1,
		)

		if len(request):
			data = frappe.db.get_value("Integration Request", request[0].name, "data")
			data = frappe._dict(json.loads(data))

			payment_gateway = data.get("payment_gateway")
			if payment_gateway == "Razorpay":
				payment_id = "razorpay_payment_id"
			elif "Stripe" in payment_gateway:
				payment_id = "stripe_token_id"
			elif "Paypal" in payment_gateway:
				payment_id = "transaction_id"
			else:
				payment_id = "order_id"

			frappe.db.set_value(
				"Service Appointment Payment",
				data.payment,
				{
					"payment_received": 1,
					"payment_id": data.get(payment_id),
					"order_id": data.get("order_id"),
				},
			)

			try:
				# Confirm the payment has gone through
				self.db_set("payment_status", "Paid")
				self.db.set("status", "Confirmed")
				self.submit()
			except Exception:
				frappe.log_error(_("Appointment Confirmation Failed"), frappe.get_traceback())

	def update_mpesa_payment_record(self):
		try:
			self.db_set("payment_status", "Paid")
			self.db_set("status", "Confirmed")
			self.submit()
		except Exception:
			frappe.log_error(_("Appointment Confirmation Failed"), frappe.get_traceback())

	def validate_appointment_date_and_times(self):
		start_dt = get_datetime(f"{self.appointment_date} {self.start_time}")
		end_dt = get_datetime(f"{self.appointment_date} {self.end_time}")

		if start_dt >= end_dt:
			frappe.throw(_("End Time must be after Start Time"))

		if start_dt < now_datetime():
			frappe.throw(_("You cannot schedule an appointment in the past"))

	def calculate_actual_duration(self):
		"""Validate actual end time and calculate actual duration when appointment is completed"""

		actual_start_dt = get_datetime(f"{self.appointment_date} {self.actual_start_time}")
		actual_end_dt = get_datetime(f"{self.appointment_date} {self.actual_end_time}")

		if actual_end_dt <= actual_start_dt:
			frappe.throw(
				_("Actual End Time must be after Start Time"),
				title=_("Invalid Actual End Time"),
			)

		# Calculate actual duration in minutes
		duration_delta = actual_end_dt - actual_start_dt
		actual_duration_mins = int(duration_delta.total_seconds() / 60)
		self.db_set("actual_duration", actual_duration_mins, update_modified=False)

	def validate_overlaps(self):
		"""
		Validate that the appointment does not overlap with existing appointments
		for the same provider on the same date and time range.
		"""
		if not self.appointment_provider or not all([self.appointment_date, self.start_time, self.end_time]):
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

	def validate_required_for_billing(self):
		"""Validate required fields before creating billing documents"""
		required_fields = {
			"customer": "Customer",
			"company": "Company",
			"appointment_type": "Service Type",
		}

		missing_fields = [label for field, label in required_fields.items() if not self.get(field)]

		if missing_fields:
			frappe.throw(
				_("The following fields are required to confirm appointment: {0}").format(
					", ".join(missing_fields)
				)
			)

	def validate_appointment_capacity(self):
		"""Check if service unit or service provider has capacity for this appointment"""
		if not self.appointment_type:
			return

		requires_unit, unit_types = service_type_requires_service_unit(self.appointment_type)
		apt_type = frappe.get_doc("Service Type", self.appointment_type)
		max_clients = apt_type.max_clients_per_slot or 1

		if requires_unit and self.service_unit:
			capacity_ok = check_service_unit_capacity(
				self.service_unit,
				self.appointment_date,
				self.start_time,
				self.end_time,
				self.appointment_type,
				max_clients,
				exclude_appointment=self.name,
			)

			if not capacity_ok:
				frappe.throw(
					_("Service Unit {0} is at full capacity for the selected time slot").format(
						frappe.bold(self.service_unit)
					),
					title=_("Capacity Exceeded"),
				)

		else:
			capacity_ok = check_provider_slot_capacity(
				self.appointment_provider,
				self.appointment_date,
				self.start_time,
				self.end_time,
				max_clients,
				exclude_appointment=self.name,
			)

			if not capacity_ok:
				frappe.throw(
					_("Provider {0} is at full capacity for the selected time slot (max: {1})").format(
						frappe.bold(self.appointment_provider), max_clients
					),
					title=_("Capacity Exceeded"),
				)

	def assign_service_unit_to_appointment(self):
		"""
		Assign service unit to appointment based on booked slots
		Called from Service Appointment's before_save or validate
		"""
		if not self.selected_slot_ids:
			return

		requires_unit, _unit_types = service_type_requires_service_unit(self.appointment_type)

		if not requires_unit:
			self.service_unit = None
			return

		slot_ids = (
			json.loads(self.selected_slot_ids)
			if isinstance(self.selected_slot_ids, str)
			else self.selected_slot_ids
		)

		if not slot_ids:
			return

		# Get service unit from the first slot
		first_slot = frappe.db.get_value(
			"Service Provider Appointment Slot",
			slot_ids[0],
			["service_unit", "provider"],
			as_dict=True,
		)

		if first_slot:
			self.service_unit = first_slot.service_unit
			self.appointment_provider = first_slot.provider

	def validate_service_unit_requirement(self):
		"""
		Validate that service unit is provided when required
		Called from Service Appointment's validate method
		"""
		if not self.appointment_type:
			return

		requires_unit, unit_types = service_type_requires_service_unit(self.appointment_type)

		if requires_unit and not self.service_unit:
			frappe.throw(
				_("Service Unit is required for appointment type {0}. " "Required unit types: {1}").format(
					frappe.bold(self.appointment_type), ", ".join(unit_types)
				),
				title=_("Service Unit Required"),
			)

		# Validate that the assigned service unit matches the required type
		if self.service_unit:
			service_unit_doc = frappe.get_doc("Service Unit", self.service_unit)

			if requires_unit and service_unit_doc.unit_type not in unit_types:
				frappe.throw(
					_("Service Unit {0} is of type {1}, but this appointment requires: {2}").format(
						frappe.bold(self.service_unit),
						frappe.bold(service_unit_doc.unit_type),
						", ".join(unit_types),
					),
					title=_("Invalid Service Unit Type"),
				)

	def validate_price_and_currency(self):
		if not self.appointment_type or not self.appointment_price:
			frappe.throw("Service Type and Service Price are required to validate the price.")

		self.validate_guest_requirements()

		price_record = self.get_selected_price_record()

		if not price_record:
			frappe.throw(
				f"No matching price found for '{self.appointment_price}' in service '{self.appointment_type}'"
			)

		grand_total = self.calculate_total_with_guests(price_record)
		currency = price_record.currency

		if not self.total_amount or not self.grand_total or self.total_amount != grand_total:
			self.total_amount = grand_total
			self.grand_total = grand_total
			self.currency = currency

		if self.currency != currency:
			self.currency = currency

	def validate_guest_requirements(self):
		"""Validate guest count against service type requirements"""
		if not self.appointment_type:
			return

		service_type = frappe.get_doc("Service Type", self.appointment_type, ignore_permissions=True)

		guest_count = len(self.guests) if self.guests else 1
		self.total_guests = guest_count

		if service_type.min_guests and guest_count < service_type.min_guests:
			frappe.throw(
				title=_("Minimum Guests Required"),
				msg=_("This service requires a minimum of {0} guests. You have {1}.").format(
					service_type.min_guests, guest_count
				),
			)

		if service_type.max_guests and guest_count > service_type.max_guests:
			frappe.throw(
				title=_("Maximum Guests Exceeded"),
				msg=_("This service allows a maximum of {0} guests. You have {1}.").format(
					service_type.max_guests, guest_count
				),
			)

	def get_selected_price_record(self):
		"""Return the price, given service_type and appointment_price_name"""

		if not self.appointment_type or not self.appointment_price:
			return None

		prices = frappe.get_all(
			"Service Type Price",
			filters={
				"parent": self.appointment_type,
				"price_name": self.appointment_price,
			},
			fields=[
				"name",
				"price_name",
				"amount",
				"currency",
				"pricing_model",
				"guest_count",
			],
		)

		if not prices:
			return None

		guest_count = self.total_guests or 1

		for price in prices:
			pricing_model = price.pricing_model

			if pricing_model == "Guest Tier":
				if price.guest_count and price.guest_count <= guest_count:
					return price

			else:
				return price

		return prices[0] if prices else None

	def calculate_total_with_guests(self, price_record):
		"""Calculate total amount based on pricing model and guest count"""
		if not price_record:
			return 0

		base_amount = flt(price_record.amount)
		pricing_model = price_record.pricing_model
		guest_count = self.total_guests or 1

		if pricing_model == "Per Guest":
			return flt(base_amount) * guest_count

		elif pricing_model == "Guest Tier":
			return base_amount

		else:
			# Per Booking: Flat rate regardless of guests
			return flt(base_amount)

	def apply_coupon_if_any(self):
		if not self.coupon_code:
			self.discount_amount = 0
			return

		coupon = frappe.get_doc("Service Appointment Coupon Code", self.coupon_code)

		is_valid, msg = coupon.is_valid_for_appointment(appointment=self)

		if not is_valid:
			frappe.throw(msg)

		is_available, msg = coupon.is_usage_available()
		if not is_available:
			frappe.throw(msg)

		self.discount_amount = self.compute_coupon_discount(coupon)

	def compute_coupon_discount(self, coupon):
		total = flt(self.total_amount)

		if coupon.discount_type == "Percentage":
			discount = total * (coupon.discount_value / 100)
		else:
			discount = flt(coupon.discount_value)

		if coupon.maximum_discount_amount:
			discount = min(discount, coupon.maximum_discount_amount)

		discount = min(discount, total)

		return flt(discount)

	def calculate_grand_total(self):
		total = flt(self.total_amount)
		discount = flt(self.discount_amount)

		self.grand_total = max(total - discount, 0)

	def set_company_from_type(self):
		return frappe.db.get_value("Service Type", self.appointment_type, "company")

	def set_duration_from_type(self):
		"""Set duration from appointment type"""
		duration = frappe.db.get_value(
			"Service Type Price",
			{"parent": self.appointment_type, "price_name": self.appointment_price},
			"duration",
		)
		if duration:
			self.duration = duration

	def insert_calendar_event(self):
		if not self.appointment_provider:
			return

		starts_on = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.start_time))
		ends_on = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.end_time))

		google_calendar = frappe.db.get_value(
			"Service Provider", self.appointment_provider, "google_calendar"
		)
		if not google_calendar:
			google_calendar = frappe.db.get_single_value(
				"Service Appointment Settings", "default_google_calendar"
			)

		color = frappe.db.get_value("Service Provider", self.appointment_provider, "color_code")
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
				"add_video_conferencing": (1 if self.add_video_conferencing and google_calendar else 0),
				"google_calendar": google_calendar,
				"description": f"{self.name} - {self.company}",
				"pulled_from_google_calendar": 0,
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
			}
		)
		participants = []

		participants.append(
			{
				"reference_doctype": "Service Provider",
				"reference_docname": self.appointment_provider,
			}
		)

		if self.customer:
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
				frappe.log_error(
					_("Appointment Confirmation Message Not Sent"),
					frappe.get_traceback(),
				)
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

	def _slots_already_booked(self):
		"""Check if slots are already booked for this appointment"""
		if not self.name:
			return False

		booked_count = frappe.db.count(
			"Service Provider Appointment Slot", {"service_appointment": self.name}
		)
		return booked_count > 0

	def book_selected_slots(self):
		"""Book the selected slots"""
		try:
			slot_ids = json.loads(self.selected_slot_ids)
		except (json.JSONDecodeError, TypeError):
			frappe.throw(_("Invalid slot selection data"))

		# Validate all slots are still available
		for slot_id in slot_ids:
			slot = frappe.get_doc("Service Provider Appointment Slot", slot_id)

			if not slot.is_available or (slot.service_appointment and slot.service_appointment != self.name):
				frappe.throw(
					_("Slot {0} is no longer available. Please select another time slot.").format(slot_id),
					title=_("Slot Not Available"),
				)

		# Book all slots
		for slot_id in slot_ids:
			frappe.db.set_value(
				"Service Provider Appointment Slot",
				slot_id,
				{"service_appointment": self.name, "is_available": 0},
			)

	def release_slots(self):
		"""Release all booked slots for this appointment"""
		from frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
			release_appointment_slots,
		)

		release_appointment_slots(self.name)

	def handle_status_change(self):
		"""Handle actions based on status change"""
		if self.status == "Cancelled":
			self.handle_cancellation()

	def complete_appointment(self):
		self.calculate_actual_duration()
		self.auto_issue_consumables()
		self.complete_linked_event()

		invoice_name = self.create_sales_invoice()

		return invoice_name

	@frappe.whitelist()
	def complete_and_invoice(self, actual_start_time: str, actual_end_time: str) -> str:
		self.actual_start_time = actual_start_time
		self.actual_end_time = actual_end_time
		self.status = "Completed"
		self.save()

		invoice_name = self.complete_appointment()

		return invoice_name

	def get_linked_document(self, doctype, fields=None):
		"""Generic method to get linked document"""
		if fields is None:
			fields = ["name"]

		direct_link_field = doctype.lower().replace(" ", "_")
		if hasattr(self, direct_link_field) and self.get(direct_link_field):
			doc = frappe.get_doc(doctype, self.get(direct_link_field))
			if doc.docstatus == 1:
				return {field: doc.get(field) for field in fields}
			return None

		docs = frappe.get_all(
			doctype,
			filters={"service_appointment": self.name, "docstatus": 1},
			fields=fields,
			limit=1,
		)
		return docs[0] if docs else None

	def get_all_linked_documents(self):
		"""Get all linked documents for checking before deletion"""
		doctypes = {
			"Sales Invoice": "sales_invoice",
			"Stock Entry": "stock_entry",
			"Material Request": "material_request",
		}

		linked_docs = []

		for doctype, field in doctypes.items():
			# Check if direct link exists
			if self.get(field):
				doc = frappe.db.get_value(doctype, self.get(field), ["name", "docstatus"], as_dict=True)
				if doc and doc.docstatus != 2:
					status = "Draft" if doc.docstatus == 0 else "Submitted"
					linked_docs.append({"doctype": doctype, "name": doc.name, "status": status})
			else:
				# Check custom field
				docs = frappe.get_all(
					doctype,
					filters={"service_appointment": self.name, "docstatus": ["!=", 2]},
					fields=["name", "docstatus"],
				)
				for doc in docs:
					status = "Draft" if doc.docstatus == 0 else "Submitted"
					linked_docs.append({"doctype": doctype, "name": doc.name, "status": status})

		return linked_docs

	def check_linked_documents_before_delete(self):
		"""Check if any billing or stock documents are linked to this appointment"""
		linked_docs = self.get_all_linked_documents()

		linked_docs = [doc for doc in linked_docs if doc.get("doctype") != "Event"]

		if linked_docs:
			doc_list = "<br>".join(
				[
					f"• {doc['doctype']}: {get_link_to_form(doc['doctype'], doc['name'])} ({doc['status']})"
					for doc in linked_docs
				]
			)

			frappe.throw(
				_(
					"Cannot delete this appointment because the following documents are linked to it:<br><br>{0}<br><br>Please cancel or delete these documents first."
				).format(doc_list),
				title=_("Linked Documents Exist"),
			)

	def complete_linked_event(self):
		"""Complete linked event if appointment is in Completed"""
		if not self.event:
			return

		try:
			event_status = frappe.db.get_value("Event", self.event, "status")

			if event_status == "Open":
				frappe.db.set_value("Event", self.event, "status", "Completed")

		except Exception as e:
			frappe.log_error(
				title=f"Event Completion Failed for Appointment {self.name}",
				message=f"Failed to complete event {self.event}: {e}",
			)

	def delete_linked_event(self):
		"""Delete linked event if appointment is in draft or if it's the only linked document"""
		if not self.event:
			return

		try:
			frappe.delete_doc("Event", self.event, force=True, ignore_permissions=True)
		except Exception as e:
			frappe.log_error(
				title=f"Event Deletion Failed for Appointment {self.name}",
				message=f"Failed to delete event {self.event}: {e}",
			)

	def cancel_linked_event(self):
		"""Cancel linked event if appointment is submitted"""
		if not self.event:
			return

		try:
			event_status = frappe.db.get_value("Event", self.event, "status")

			if event_status == "Open":
				frappe.db.set_value("Event", self.event, "status", "Cancelled")
		except Exception as e:
			frappe.log_error(
				title=f"Event Cancellation Failed for Appointment {self.name}",
				message=f"Failed to cancel event {self.event}: {e}",
			)

	def get_selected_price(self, apt_type):
		"""Get the selected price from appointment type"""
		if self.appointment_price:
			for price in apt_type.prices:
				if price.price_name == self.appointment_price:
					return price

		elif apt_type.prices:
			return apt_type.prices[0]

		return None

	def create_sales_invoice(self):
		"""Create Sales Invoice when appointment is completed"""
		sales_invoice = self.get_linked_document("Sales Invoice")

		if sales_invoice:
			self.show_already_exists_message("Sales Invoice", sales_invoice.name)
			return

		item_code = frappe.db.get_value("Service Type", self.appointment_type, "item")
		price_record = self.get_selected_price_record()
		qty, rate = self.get_invoice_qty_and_rate(price_record)

		try:
			si = frappe.get_doc(
				{
					"doctype": "Sales Invoice",
					"company": self.company,
					"customer": self.customer,
					"posting_date": today(),
					"payment_due_date": today(),
					"currency": self.currency,
					"items": [
						{
							"item_code": item_code,
							"qty": qty,
							"rate": rate,
						}
					],
					"service_appointment": self.name,
					"allocate_advances_automatically": True,
					"apply_discount_on": "Grand Total",
					"discount_amount": flt(self.discount_amount or 0),
				}
			)
			si.insert(ignore_permissions=True, ignore_mandatory=True)

			return si.name

		except Exception as e:
			self.log_and_throw_error("Sales Invoice", e)

	def get_invoice_qty_and_rate(self, price_record):
		pricing_model = price_record.pricing_model
		guest_count = self.total_guests or 1
		base_amount = flt(price_record.amount)

		if pricing_model == "Per Guest":
			return guest_count, base_amount

		elif pricing_model == "Guest Tier":
			return 1, base_amount

		else:
			return 1, base_amount

	def handle_cancellation(self):
		"""Handle appointment cancellation"""
		# Release slots
		self.db_set("status", "Cancelled")
		self.db_set("cancellation_date", now_datetime())
		self.cancel_linked_event()
		self.release_slots()

	def auto_issue_consumables(self):
		"""Auto issue consumables if setting is enabled"""
		if frappe.db.get_single_value("Service Appointment Settings", "auto_issue_consumables"):
			self.issue_consumables()

	def issue_consumables(self):
		"""Issue consumables via Stock Entry when appointment is completed"""

		stock_entry = self.get_linked_document("Stock Entry")

		if stock_entry:
			self.show_already_exists_message("Stock Entry", stock_entry.name)
			return

		if not self.appointment_type:
			return

		apt_type = frappe.get_doc("Service Type", self.appointment_type)

		if not hasattr(apt_type, "consumables") or not apt_type.consumables:
			return

		try:
			source_warehouse = self.get_source_warehouse

			if not source_warehouse:
				frappe.msgprint(
					_("Please set Default Consumables Warehouse in Service Appointment Settings"),
					indicator="orange",
					alert=True,
				)
				return

			# Create Stock Entry for Material Issue
			stock_entry = frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Issue",
					"company": self.company,
					"posting_date": getdate(),
					"service_appointment": self.name,
					"items": self.get_stock_entry_items(apt_type),
				}
			)

			stock_entry.insert(ignore_permissions=True)
			stock_entry.submit()

			self.show_success_message("Stock Entry", stock_entry.name)

		except Exception as e:
			self.log_error("issue consumables", e)
			frappe.msgprint(
				_("Failed to issue consumables: {0}").format(str(e)),
				indicator="red",
				alert=True,
			)

	def get_stock_entry_items(self, apt_type):
		"""Get items for stock entry from appointment type consumables"""
		items = []

		for consumable in apt_type.consumables:
			items.append(
				{
					"item_code": consumable.item,
					"qty": consumable.qty or 1,
					"uom": consumable.uom or "Nos",
					"s_warehouse": consumable.s_warehouse,
					"cost_center": consumable.cost_center,
				}
			)
		return items

	def create_material_request_for_consumables(self, t_warehouse):
		"""Create Material Request for consumables"""
		material_request = self.get_linked_document("Material Request")

		if material_request:
			self.show_already_exists_message("Material Request", material_request.name)
			return material_request

		if not self.appointment_type:
			return

		apt_type = frappe.get_doc("Service Type", self.appointment_type)

		if not hasattr(apt_type, "consumables") or not apt_type.consumables:
			frappe.msgprint(_("No consumables configured for this appointment type"))
			return

		try:
			# Create Material Request
			mr = frappe.get_doc(
				{
					"doctype": "Material Request",
					"material_request_type": "Material Transfer",
					"company": self.company,
					"transaction_date": getdate(),
					"schedule_date": self.appointment_date,
					"service_appointment": self.name,
					"items": self.get_material_request_items(apt_type, t_warehouse),
				}
			)

			mr.insert(ignore_permissions=True)
			self.show_success_message("Material Request", mr.name)

			return mr.name

		except Exception as e:
			self.log_and_throw_error("Material Request", e)

	def get_material_request_items(self, apt_type, t_warehouse):
		"""Get items for material request from appointment type consumables"""
		items = []
		for consumable in apt_type.consumables:
			items.append(
				{
					"item_code": consumable.item,
					"qty": consumable.qty,
					"uom": consumable.uom,
					"warehouse": t_warehouse,
					"schedule_date": self.appointment_date,
				}
			)
		return items

	def show_already_exists_message(self, doctype, docname):
		"""Show message when document already exists"""
		frappe.msgprint(
			_("{0} {1} already exists for this appointment").format(
				doctype, get_link_to_form(doctype, docname)
			),
			indicator="blue",
			alert=True,
		)

	def show_success_message(self, doctype, docname):
		"""Show success message after document creation"""
		frappe.msgprint(
			_("{0} {1} created successfully").format(doctype, get_link_to_form(doctype, docname)),
			indicator="green",
			alert=True,
		)

	def log_error(self, operation, error):
		"""Log error without throwing"""
		frappe.log_error(
			title=_("Failed to {0} for Appointment {1}").format(operation, self.name),
			message=frappe.get_traceback(),
		)

	def log_and_throw_error(self, doctype, error):
		"""Log error and throw exception"""
		self.log_error(f"create {doctype}", error)
		frappe.throw(_("Failed to create {0}: {1}").format(doctype, str(error)))


@frappe.whitelist()
def get_appointment_slots(appointment_type, duration, provider=None, date=None, days_ahead=30):
	"""
	Wrapper method for getting available slots
	Can be called from frontend
	"""
	from frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
		get_available_slots,
	)

	return get_available_slots(appointment_type, duration, provider, date, days_ahead)


@frappe.whitelist()
def issue_consumables_manual(appointment):
	"""Manually issue consumables for an appointment"""
	doc = frappe.get_doc("Service Appointment", appointment)
	doc.issue_consumables()
	return doc.stock_entry


@frappe.whitelist()
def create_material_request_manual(appointment, t_warehouse):
	"""Manually create material request for consumables"""
	doc = frappe.get_doc("Service Appointment", appointment)
	return doc.create_material_request_for_consumables(t_warehouse)


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""

	conditions = get_event_conditions("Service Appointment", filters)
	match_conditions = build_match_conditions("Service Appointment")

	if match_conditions:
		conditions += "and" + match_conditions

	data = frappe.db.sql(
		f"""
		select
			`tabService Appointment`.name,
			`tabService Appointment`.customer,
			`tabService Appointment`.appointment_provider,
			`tabService Appointment`.status,
			`tabService Appointment`.duration,
			timestamp(
				`tabService Appointment`.appointment_date,
				`tabService Appointment`.start_time
			) as start,
			`tabService Provider`.color_code as color
		from
			`tabService Appointment`
		left join `tabService Provider`
			on `tabService Appointment`.appointment_provider = `tabService Provider`.name
		where
			(`tabService Appointment`.appointment_date between %(start)s and %(end)s)
			and `tabService Appointment`.status != 'Cancelled'
			and `tabService Appointment`.docstatus < 2
			{conditions}
		""",
		{"start": start, "end": end},
		as_dict=True,
		update={"allDay": 0},
	)

	for item in data:
		item.end = item.start + datetime.timedelta(minutes=item.duration)

	return data


@frappe.whitelist()
def cancel_old_appointment(old_appointment_name, new_appointment_name):
	"""
	Cancel the old appointment after a successful reschedule.
	Called from the frontend after the new appointment is created.

	:param old_appointment_name: Name of the old appointment to cancel
	:param new_appointment_name: Name of the new appointment (for reference)
	"""
	try:
		old_appointment = frappe.get_doc("Service Appointment", old_appointment_name)

		if old_appointment.status in ["Cancelled", "Closed", "Rescheduled"]:
			return {
				"success": True,
				"message": _("Appointment is already cancelled or closed"),
			}

		# Validate that appointment can be cancelled
		if old_appointment.docstatus != 1:
			frappe.throw(_("Only submitted appointments can be cancelled"))

		# Add comment linking to new appointment
		old_appointment.add_comment(
			"Comment",
			_("Rescheduled to {0}").format(get_link_to_form("Service Appointment", new_appointment_name)),
		)

		# Cancel the appointment
		old_appointment.flags.ignore_permissions = True
		old_appointment.flags.ignore_links = True
		old_appointment.cancel()

		# Set rescheduled_to field to link to the new appointment
		frappe.db.set_value(
			"Service Appointment",
			old_appointment.name,
			{"rescheduled_to": new_appointment_name, "status": "Rescheduled"},
		)

		frappe.db.commit()

		return {
			"success": True,
			"message": _("Appointment {0} has been cancelled and linked to {1}").format(
				old_appointment_name, new_appointment_name
			),
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title=_("Failed to Cancel Old Appointment"),
			message=f"Failed to cancel appointment {old_appointment_name} during reschedule: {e}\n\n{frappe.get_traceback()}",
		)
		frappe.throw(_("Failed to cancel old appointment: {0}").format(str(e)))


@frappe.whitelist()
def reschedule_appointment(
	appointment_name: str,
	new_appointment_date: str,
	new_start_time: str,
	new_end_time: str,
	new_provider: str | None = None,
	new_slot_ids: str | None = None,
	new_service_unit: str | None = None,
) -> dict:
	"""
	Reschedule an existing appointment by creating a new one and cancelling the old one.

	:param appointment_name: Name of the appointment to reschedule
	:param new_appointment_date: New appointment date
	:param new_start_time: New start time
	:param new_end_time: New end time
	:param new_provider: Optional new provider (if changing provider)
	:param new_slot_ids: Optional new slot IDs (JSON string or list)
	:param new_service_unit: Optional new service unit
	"""
	# Get the old appointment
	old_appointment = frappe.get_doc("Service Appointment", appointment_name)

	# Validate that appointment can be rescheduled
	if old_appointment.docstatus != 1:
		frappe.throw(_("Only submitted appointments can be rescheduled"))

	if old_appointment.status in ["Cancelled", "Closed", "No Show"]:
		frappe.throw(_("Cannot reschedule cancelled, closed, or no-show appointments"))

	if old_appointment.status == "Completed":
		frappe.throw(_("Cannot reschedule completed appointments"))

	# Validate new datetime is in the future
	new_start_dt = get_datetime(f"{new_appointment_date} {new_start_time}")
	if new_start_dt < now_datetime():
		frappe.throw(_("Cannot reschedule to a time in the past"))

	try:
		# Create new appointment with same details but new date/time
		new_appointment = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"customer": old_appointment.customer,
				"full_name": old_appointment.full_name,
				"mobile_no": old_appointment.mobile_no,
				"email": old_appointment.email,
				"company": old_appointment.company,
				"appointment_type": old_appointment.appointment_type,
				"appointment_provider": new_provider or old_appointment.appointment_provider,
				"appointment_date": new_appointment_date,
				"start_time": new_start_time,
				"end_time": new_end_time,
				"duration": old_appointment.duration,
				"service_unit": new_service_unit or old_appointment.service_unit,
				"appointment_price": old_appointment.appointment_price,
				"total_amount": old_appointment.total_amount,
				"grand_total": old_appointment.grand_total,
				"currency": old_appointment.currency,
				"details": old_appointment.details,
				"notes": (old_appointment.notes or "") + f"\n\nRescheduled from: {old_appointment.name}",
				"status": "Confirmed",
				"source": old_appointment.source,
				"add_video_conferencing": old_appointment.add_video_conferencing,
				"rescheduled_from": old_appointment.name,
				# "guests": old_appointment.guests,
			}
		)

		# Copy guests from old appointment
		if old_appointment.guests:
			for guest in old_appointment.guests:
				new_appointment.append(
					"guests",
					{
						"full_name": guest.full_name,
						"email": guest.email,
						"mobile_no": guest.mobile_no,
					},
				)

		# Handle slot IDs if provided
		if new_slot_ids:
			if isinstance(new_slot_ids, str):
				new_appointment.selected_slot_ids = new_slot_ids
			else:
				new_appointment.selected_slot_ids = json.dumps(new_slot_ids)

		# Insert and submit the new appointment
		new_appointment.insert(ignore_permissions=True)
		new_appointment.submit()

		# Cancel the old appointment
		old_appointment.add_comment(
			"Comment",
			_("Appointment rescheduled to {0} at {1}. New appointment: {2}").format(
				frappe.format(new_appointment_date, {"fieldtype": "Date"}),
				new_start_time,
				get_link_to_form("Service Appointment", new_appointment.name),
			),
		)

		old_appointment.flags.ignore_permissions = True
		old_appointment.flags.ignore_links = True
		old_appointment.cancel()
		old_appointment.db_set("status", "Rescheduled")

		frappe.db.commit()

		return {
			"success": True,
			"new_appointment": new_appointment.name,
			"old_appointment": old_appointment.name,
			"message": _("Appointment rescheduled successfully. New appointment: {0}").format(
				get_link_to_form("Service Appointment", new_appointment.name)
			),
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title=_("Appointment Reschedule Failed"),
			message=f"Failed to reschedule appointment {appointment_name}: {e}\n\n{frappe.get_traceback()}",
		)
		frappe.throw(_("Failed to reschedule appointment: {0}").format(str(e)))


@frappe.whitelist()
def cancel_appointment(appointment_id, cancellation_reasons=None):
	"""Cancel a submitted appointment"""
	try:
		appointment = frappe.get_doc("Service Appointment", appointment_id)

		if appointment.docstatus != 1:
			frappe.throw(_("Only submitted appointments can be cancelled"))

		if appointment.status in ["Cancelled", "Closed"]:
			return {"success": True, "message": _("Appointment is already cancelled")}

		if cancellation_reasons:
			if isinstance(cancellation_reasons, str):
				try:
					cancellation_reasons = json.loads(cancellation_reasons)
				except Exception:
					cancellation_reasons = [cancellation_reasons]

			appointment.cancellation_reasonss = []

			for reason in cancellation_reasons:
				appointment.append("cancellation_reasons", {"reason": reason})

		appointment.flags.ignore_permissions = True
		appointment.cancel()

		frappe.db.commit()

		return {
			"success": True,
			"message": _("Appointment cancelled successfully"),
			"appointment": appointment_id,
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title=_("Appointment Cancellation Failed"),
			message=f"Failed to cancel appointment {appointment_id}: {e}\n\n{frappe.get_traceback()}",
		)
		frappe.throw(_("Failed to cancel appointment: {0}").format(str(e)))
