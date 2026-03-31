# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class ServiceBooking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_booking_item.service_booking_item import ServiceBookingItem

		booking_date: DF.Date
		currency: DF.Link | None
		customer: DF.Link
		email: DF.Data | None
		full_name: DF.Data | None
		grand_total: DF.Currency
		items: DF.Table[ServiceBookingItem]
		mobile_no: DF.Data | None
		naming_series: DF.Literal["BK-.DD./.MM./.YY.-.####"]
		outstanding_amount: DF.Currency
		status: DF.Literal["Draft", "Confirmed", "Cancelled"]
		subtotal: DF.Currency
		total_guests: DF.Int
	# end: auto-generated types

	def on_load(self):
		self.set_onload("appointment_list_html", self.get_appointment_table())

	def validate(self):
		self.recalculate_totals()

	def recalculate_totals(self):
		total = 0
		guests = 0
		for item in self.items:
			total += flt(item.total_amount)
			guests += cint(item.qty)

		self.subtotal = total
		self.total_guests = guests

		self.grand_total = self.subtotal

		if flt(self.outstanding_amount) == 0 or self.is_new():
			self.outstanding_amount = self.grand_total

	def update_outstanding_amount(self):
		total_paid = (
			frappe.db.get_value(
				"Service Appointment Payment Reference",
				{"reference_doctype": "Service Booking", "reference_name": self.name, "docstatus": 1},
				"sum(allocated_amount)",
			)
			or 0
		)

		self.outstanding_amount = flt(self.grand_total) - flt(total_paid)

	@frappe.whitelist()
	def add_guest(self, guest_data):
		if isinstance(guest_data, str):
			guest_data = frappe.parse_json(guest_data)

		service_type = guest_data.get("service_type")
		price_id = guest_data.get("price_id")

		price_doc = frappe.db.get_value(
			"Service Type Price",
			{"price_name": price_id, "parent": service_type},
			["pricing_model", "amount", "currency", "duration"],
			as_dict=True,
		)

		if not price_doc:
			frappe.throw(f"Price '{price_id}' not found for {service_type}")

		# 1. Initialize the Service Appointment
		appointment = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"booking_id": self.name,
				"appointment_type": service_type,
				"appointment_date": guest_data.get("date"),
				"appointment_provider": guest_data.get("provider"),
				"duration": price_doc.duration,
				"appointment_price": price_id,
				"currency": price_doc.currency,
				"start_time": guest_data.get("start_time"),
				"end_time": guest_data.get("end_time"),
				"selected_slot_ids": json.dumps(guest_data.get("slot_ids", [])),
				"customer": self.customer,
				# top-level fields
				"total_amount": price_doc.amount,
				"source": "Desk",
				"status": "Open",
			}
		)

		# 2. Add the Guest to the mandatory child table
		appointment.append(
			"guests",
			{
				"full_name": guest_data.get("guest_name"),
				"email": guest_data.get("guest_email"),
				"mobile_no": guest_data.get("guest_mobile"),
				"is_primary": 1,
				"notes": guest_data.get("notes"),
			},
		)

		# 3. Now insert will pass validation
		appointment.insert(ignore_permissions=True)

		# 4. Update the parent Service Booking ledger
		item_found = False
		for row in self.items:
			if row.service_type == service_type and row.rate == price_doc.amount:
				row.qty += 1
				row.total_amount = row.qty * row.rate
				item_found = True
				break

		if not item_found:
			self.append(
				"items",
				{
					"service_type": service_type,
					"qty": 1,
					"pricing_model": price_doc.pricing_model,
					"rate": price_doc.amount,
					"total_amount": price_doc.amount,
					"currency": price_doc.currency,
				},
			)

		self.save(ignore_permissions=True)

		return {"appointment": appointment.name, "grand_total": self.grand_total}

	@frappe.whitelist()
	def get_appointment_table(self):
		appointments = frappe.get_all(
			"Service Appointment",
			filters={"booking_id": self.name, "status": ["not in", ["Rescheduled"]]},
			fields=[
				"name",
				"appointment_date",
				"appointment_type",
				"service_provider_name",
				"start_time",
				"status",
				"total_amount",
				"rescheduled_to",
				"rescheduled_from",
			],
			order_by="appointment_date asc, start_time asc",
		)

		if not appointments:
			return "<div class='text-muted'>No appointments linked yet.</div>"

		appt_names = [a.name for a in appointments]
		guest_list = frappe.get_all(
			"Service Appointment Guest",
			filters={"parent": ["in", appt_names]},
			fields=["parent", "full_name"],
		)

		guest_map = {g.parent: g.full_name for g in guest_list}

		html = """
		<table class="table table-bordered" style="cursor: pointer; background-color: #f8f9fa;">
			<thead>
				<tr style="background-color: #ebeff2;">
					<th>Guest Appointment</th>
					<th>Service / Provider</th>
					<th>Date & Time</th>
					<th>Status</th>
					<th class="text-right">Total</th>
				</tr>
			</thead>
			<tbody>
		"""

		for appt in appointments:
			guest_name = guest_map.get(appt.name, "Unspecified Guest")
			is_history = appt.status in ["Rescheduled", "Cancelled"]
			row_style = "opacity: 0.6; background-color: #f1f1f1;" if is_history else ""

			reschedule_info = ""
			if appt.status == "Rescheduled" and appt.rescheduled_to:
				reschedule_info = f"""
					<div style="margin-top: 4px;">
						<span class="label label-warning" style="font-size: 0.75em;">
							{_("Moved to")} {appt.rescheduled_to}
						</span>
					</div>
				"""

			# Case 2: This is a NEW appointment that came from an old one
			elif appt.rescheduled_from:
				reschedule_info = f"""
					<div style="margin-top: 4px;">
						<span class="label label-default" style="font-size: 0.75em; background-color: #e2e2e2; color: #666;">
							{_("From")} {appt.rescheduled_from}
						</span>
					</div>
				"""

			service_info = f"<b>{appt.appointment_type}</b><br><small class='text-muted'>{appt.service_provider_name or 'Unassigned'}</small>"

			dt_info = f"{frappe.format(appt.appointment_date, 'Date')}<br><small>{appt.start_time}</small>"

			html += f"""
				<tr style="{row_style}" onclick="frappe.set_route('Form', 'Service Appointment', '{appt.name}')">
					<td>
						<div style="font-weight: bold; color: #1a1a1a;">{guest_name}</div>
						<small class='text-muted'>{appt.name}</small>
						{reschedule_info}
					</td>
					<td>{service_info}</td>
					<td>{dt_info}</td>
					<td><span class="indicator {self.get_status_color(appt.status)}">{appt.status}</span></td>
					<td class="text-right">
						<span style="text-decoration: {'line-through' if is_history else 'none'}">
							{frappe.format(appt.total_amount, 'Currency')}
						</span>
					</td>
				</tr>
			"""

		html += "</tbody></table>"
		return html

	def get_status_color(self, status):
		colors = {
			"Open": "cyan",
			"Confirmed": "blue",
			"Rescheduled": "orange",
			"Completed": "green",
			"Cancelled": "red",
		}
		return colors.get(status, "gray")
