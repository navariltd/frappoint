# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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
		status: DF.Literal["Draft", "Confirmed", "Partially Paid", "Paid", "Cancelled"]
		subtotal: DF.Currency
		total_guests: DF.Int
		total_paid: DF.Currency
	# end: auto-generated types

	def on_load(self):
		self.set_onload("appointment_list_html", self.get_appointment_table())

	@frappe.whitelist()
	def get_appointment_table(self):
		appointments = frappe.get_all(
			"Service Appointment",
			filters={"booking_id": self.name},
			fields=[
				"name",
				"appointment_type",
				"service_provider_name",
				"start_time",
				"status",
				"total_amount",
			],
			order_by="start_time asc",
		)

		if not appointments:
			return "<div class='text-muted'>No appointments linked yet.</div>"

		html = """
		<table class="table table-bordered" style="cursor: pointer; background-color: #f8f9fa;">
			<thead>
				<tr style="background-color: #ebeff2;">
					<th>ID</th>
					<th>Service</th>
					<th>Provider</th>
					<th>Time</th>
					<th>Status</th>
					<th class="text-right">Total</th>
				</tr>
			</thead>
			<tbody>
		"""

		for appt in appointments:
			status_color_map = {
				"Open": "cyan",
				"Confirmed": "blue",
				"Rescheduled": "orange",
				"Completed": "green",
				"Cancelled": "red",
				"No Show": "gray",
				"Closed": "gray",
			}

			status_color = status_color_map.get(appt.status, "gray")

			html += f"""
				<tr onclick="frappe.set_route('Form', 'Service Appointment', '{appt.name}')">
					<td><a href="/app/service-appointment/{appt.name}">{appt.name}</a></td>
					<td>{appt.appointment_type}</td>
					<td>{appt.service_provider_name or 'Unassigned'}</td>
					<td>{appt.start_time}</td>
					<td><span class="indicator {status_color}">{appt.status}</span></td>
					<td class="text-right font-weight-bold">{frappe.format(appt.total_amount, 'Currency')}</td>
				</tr>
			"""

		html += "</tbody></table>"
		return html
