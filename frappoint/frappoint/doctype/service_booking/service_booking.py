# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
import json

from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, today
from frappe.query_builder.functions import Sum

from frappoint.frappoint.services.booking_transaction_service import confirm_held_allocations
from frappoint.frappoint.services.pricing_service import (
	sync_booking_pricing_fields,
	validate_booking_coupon_assignment,
)
from frappoint.payments import get_confirmation_deposit_percent


class ServiceBooking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_booking_item.service_booking_item import ServiceBookingItem

		amended_from: DF.Link | None
		appointment_discount_total: DF.Currency
		booking_date: DF.Date
		booking_discount_amount: DF.Currency
		booking_time: DF.Time
		confirmation_required_amount: DF.Currency
		coupon_applied: DF.Check
		coupon_code: DF.Data | None
		coupon_discount_amount: DF.Currency
		coupon_discount_type: DF.Literal["", "percentage", "fixed"] #type: ignore[assignment]
		coupon_scope: DF.Literal["", "booking"] #type: ignore[assignment]
		currency: DF.Link | None
		customer: DF.Link
		email: DF.Data | None
		full_name: DF.Data | None
		grand_total: DF.Currency
		items: DF.Table[ServiceBookingItem]
		mobile_no: DF.Data | None
		naming_series: DF.Literal["BK-.DD./.MM./.YY.-.####"] #type: ignore[assignment]
		outstanding_amount: DF.Currency
		sales_invoice: DF.Link | None
		status: DF.Literal["Draft", "Payment Pending", "Partly Paid", "Confirmed", "Closed", "Cancelled"] #type: ignore[assignment]
		subtotal: DF.Currency
		total_guests: DF.Int
	# end: auto-generated types

	def on_load(self):
		self.set_onload("appointment_list_html", self.get_appointment_table())

	def validate(self):
		pricing = self.recalculate_totals()
		validate_booking_coupon_assignment(self, pricing=pricing)

	def before_submit(self):
		self.validate_submission_readiness()
		self.validate_confirmation_before_submit()

	def on_submit(self):
		if frappe.db.exists("DocType", "Service Resource Allocation"):
			for appointment_name in frappe.get_all(
				"Service Appointment", filters={"booking_id": self.name}, pluck="name"
			):
				confirm_held_allocations(appointment_name)
		self.sync_financial_snapshot()

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=False)

	def validate_submission_readiness(self):
		if not self.items:
			frappe.throw(_("Add at least one booking item before submitting."))

		appointment_count = frappe.db.count("Service Appointment", {"booking_id": self.name})
		if appointment_count <= 0:
			frappe.throw(_("Add at least one Service Appointment before submitting the booking."))

	def validate_confirmation_before_submit(self):
		total_amount = flt(self.grand_total)
		if total_amount <= 0:
			return

		self.set_confirmation_targets()
		required_amount = flt(self.confirmation_required_amount)
		paid_amount = max(0, total_amount - flt(self.outstanding_amount))

		if paid_amount < required_amount:
			frappe.throw(
				_("A minimum payment of {0} is required before this booking can be confirmed.").format(
					frappe.format(required_amount, "Currency", self.currency),
				),
				title=_("Payment Required"),
			)

	def recalculate_totals(self):
		total = 0
		guests = 0
		for item in self.items:
			total += flt(item.total_amount)
			guests += cint(item.qty)

		self.total_guests = guests
		pricing = sync_booking_pricing_fields(self)
		if not flt(self.subtotal):
			self.subtotal = total
		if not flt(self.grand_total):
			self.grand_total = flt(pricing.get("finalAmount") or total)

		appointment_names = frappe.get_all(
			"Service Appointment", filters={"booking_id": self.name}, pluck="name"
		)

		booking_paid = (
			frappe.db.get_value(
				"Service Appointment Payment",
				{"reference_doctype": self.doctype, "reference_docname": self.name, "docstatus": 1},
				Sum('amount'),
			)
			or 0
		)

		appointments_paid = 0
		if appointment_names:
			appointments_paid = (
				frappe.db.get_value(
					"Service Appointment Payment",
					{
						"reference_doctype": "Service Appointment",
						"reference_docname": ["in", appointment_names],
						"docstatus": 1,
					},
					Sum('amount')
				)
				or 0
			)

		total_paid = flt(booking_paid) + flt(appointments_paid)

		self.outstanding_amount = max(0, flt(self.grand_total) - flt(total_paid))
		self.set_confirmation_targets()
		self.set_status_from_payments(total_paid)
		return pricing

	def set_confirmation_targets(self):
		total_amount = flt(self.grand_total)
		if total_amount <= 0:
			self.confirmation_required_amount = 0
			return

		deposit_percent = flt(get_confirmation_deposit_percent("Service Booking", self.name, doc=self))
		required_amount = (total_amount * deposit_percent) / 100
		self.confirmation_required_amount = min(total_amount, flt(required_amount))

	def get_paid_amount(self):
		return max(0, flt(self.grand_total) - flt(self.outstanding_amount))

	def submit_linked_appointments_if_ready(self):
		appointment_names = frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": self.name,
				"docstatus": 0,
				"status": ["in", ["Open", "Pending Payment"]],
			},
			pluck="name",
		)

		for appointment_name in appointment_names:
			try:
				appointment = frappe.get_doc("Service Appointment", appointment_name)
				appointment.recalculate_outstanding_from_payments()
				appointment.update_payment_and_workflow_status()
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					_("Failed to auto-submit linked appointment {0}").format(appointment_name),
				)

	def maybe_auto_submit_after_payment(self):
		if self.docstatus != 0 or self.status in ["Cancelled", "Closed"]:
			return

		self.sync_financial_snapshot()
		self.submit_linked_appointments_if_ready()
		self.sync_financial_snapshot()

		if self.get_paid_amount() < flt(self.confirmation_required_amount):
			return

		self.flags.ignore_permissions = True
		self.submit()

	def set_status_from_payments(self, total_paid):
		if self.status == "Cancelled":
			return

		appointment_statuses = set(
			frappe.get_all("Service Appointment", filters={"booking_id": self.name}, pluck="status")
		)

		if not appointment_statuses:
			self.status = "Draft"
			return

		if appointment_statuses.issubset({"Cancelled", "Closed", "No Show"}):
			self.status = "Closed"
			return

		if flt(self.outstanding_amount) <= 0 and flt(self.grand_total) > 0:
			self.status = "Confirmed"
			return

		if "Pending Payment" in appointment_statuses:
			self.status = "Payment Pending"
			return

		if "Open" in appointment_statuses:
			self.status = "Payment Pending"
			return

		if flt(total_paid) > 0:
			self.status = "Partly Paid"
			return

		if appointment_statuses.intersection({"Confirmed", "Checked In", "In Progress", "Completed"}):
			self.status = "Payment Pending"
			return

		self.status = "Draft"

	def sync_financial_snapshot(self):
		"""Persist computed financial/status fields without requiring a full save."""
		self.recalculate_totals()
		self.db_set(
			{
				"coupon_code": self.coupon_code,
				"coupon_discount_type": self.coupon_discount_type,
				"coupon_discount_amount": self.coupon_discount_amount,
				"coupon_applied": self.coupon_applied,
				"coupon_scope": self.coupon_scope,
				"subtotal": self.subtotal,
				"appointment_discount_total": self.appointment_discount_total,
				"booking_discount_amount": self.booking_discount_amount,
				"total_guests": self.total_guests,
				"grand_total": self.grand_total,
				"confirmation_required_amount": self.confirmation_required_amount,
				"outstanding_amount": self.outstanding_amount,
				"status": self.status,
			},
			update_modified=False,
		)

	def update_outstanding_amount(self):
		total_paid = (
			frappe.db.get_value(
				"Service Appointment Payment Reference",
				{"reference_doctype": "Service Booking", "reference_name": self.name, "docstatus": 1},
				Sum('allocated_amount')
			)
			or 0
		)

		self.outstanding_amount = flt(self.grand_total) - flt(total_paid)

	def get_company(self):
		company = frappe.defaults.get_user_default("Company")
		if company:
			return company

		return frappe.db.get_single_value("Global Defaults", "default_company")

	def get_linked_sales_invoice(self):
		if self.sales_invoice:
			invoice = frappe.db.get_value(
				"Sales Invoice", self.sales_invoice, ["name", "docstatus"], as_dict=True
			)
			if invoice and invoice.docstatus != 2:
				return invoice

		if frappe.get_meta("Sales Invoice").has_field("service_booking"):
			invoice = frappe.get_all(
				"Sales Invoice",
				filters={"service_booking": self.name, "docstatus": ["!=", 2]},
				fields=["name", "docstatus"],
				limit=1,
			)
			if invoice:
				return invoice[0]

	def get_invoiceable_appointments(self):
		return frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": self.name,
				"status": ["not in", ["Cancelled", "Rescheduled", "Closed", "No Show"]],
			},
			fields=["name", "status"],
		)

	def get_appointment_invoice_map(self, appointment_names=None):
		filters = {"service_appointment": ["is", "set"], "docstatus": ["!=", 2]}
		if appointment_names:
			filters["service_appointment"] = ["in", appointment_names]

		invoices = frappe.get_all(
			"Sales Invoice",
			filters=filters,
			fields=["name", "service_appointment", "docstatus"],
		)
		return {invoice.service_appointment: invoice for invoice in invoices}

	def validate_invoice_readiness(self):
		if self.docstatus == 2 or self.status == "Cancelled":
			frappe.throw(_("Cannot create a Sales Invoice for a cancelled booking."))

		existing_invoice = self.get_linked_sales_invoice()
		if existing_invoice:
			frappe.throw(
				_("Sales Invoice {0} already exists for this booking.").format(existing_invoice.name),
				title=_("Already Invoiced"),
			)

		appointments = self.get_invoiceable_appointments()
		if not appointments:
			frappe.throw(_("No billable appointments are linked to this booking."))

		appointment_invoice_map = self.get_appointment_invoice_map(
			[appointment.name for appointment in appointments]
		)
		if appointment_invoice_map:
			frappe.throw(
				_("Appointment invoices already exist for this booking: {0}").format(
					", ".join(sorted(invoice.name for invoice in appointment_invoice_map.values()))
				),
				title=_("Already Invoiced"),
			)

		incomplete = [appointment.name for appointment in appointments if appointment.status != "Completed"]
		if incomplete:
			frappe.throw(
				_("Complete all linked appointments before creating the booking invoice: {0}").format(
					", ".join(incomplete)
				),
				title=_("Appointments Not Complete"),
			)

		if not self.items:
			frappe.throw(_("Add at least one booking item before creating a Sales Invoice."))

		if not self.customer:
			frappe.throw(_("Customer is required to create a Sales Invoice."))

	def build_invoice_items(self):
		items = []
		for row in self.items:
			if not row.service_type or flt(row.qty) <= 0:
				continue

			item_code = frappe.db.get_value("Service Type", row.service_type, "item")
			if not item_code:
				frappe.throw(_("Service Type {0} does not have an Item configured.").format(row.service_type))

			items.append(
				{
					"item_code": item_code,
					"qty": flt(row.qty),
					"rate": flt(row.rate),
				}
			)

		if not items:
			frappe.throw(_("No invoiceable booking items found."))

		return items

	def create_missing_payment_entries(self):
		appointment_names = frappe.get_all(
			"Service Appointment", filters={"booking_id": self.name}, pluck="name"
		)
		payment_filters = [
			["reference_doctype", "=", "Service Booking"],
			["reference_docname", "=", self.name],
			["docstatus", "=", 1],
			["payment_entry", "is", "not set"],
		]

		payment_names = frappe.get_all("Service Appointment Payment", filters=payment_filters, pluck="name")
		if appointment_names:
			payment_names.extend(
				frappe.get_all(
					"Service Appointment Payment",
					filters=[
						["reference_doctype", "=", "Service Appointment"],
						["reference_docname", "in", appointment_names],
						["docstatus", "=", 1],
						["payment_entry", "is", "not set"],
					],
					pluck="name",
				)
			)

		for payment_name in set(payment_names):
			payment = frappe.get_doc("Service Appointment Payment", payment_name)
			payment.create_payment_entry()

	@frappe.whitelist()
	def create_sales_invoice(self):
		self.validate_invoice_readiness()

		company = self.get_company()
		if not company:
			frappe.throw(_("Default company is required to create a Sales Invoice."))

		self.create_missing_payment_entries()
		items = self.build_invoice_items()
		invoice_payload = {
			"doctype": "Sales Invoice",
			"company": company,
			"customer": self.customer,
			"posting_date": today(),
			"payment_due_date": today(),
			"currency": self.currency,
			"items": items,
			"allocate_advances_automatically": True,
		}

		if frappe.get_meta("Sales Invoice").has_field("service_booking"):
			invoice_payload["service_booking"] = self.name

		item_total = sum(flt(item["qty"]) * flt(item["rate"]) for item in items)
		discount_amount = max(0, item_total - flt(self.grand_total))
		if discount_amount:
			invoice_payload["apply_discount_on"] = "Grand Total"
			invoice_payload["discount_amount"] = discount_amount

		sales_invoice = frappe.get_doc(invoice_payload)
		sales_invoice.insert(ignore_permissions=True, ignore_mandatory=True)

		self.db_set("sales_invoice", sales_invoice.name, update_modified=False)
		return sales_invoice.name

	@frappe.whitelist()
	def get_appointment_invoice_options(self):
		appointments = frappe.get_all(
			"Service Appointment",
			filters={
				"booking_id": self.name,
				"status": ["not in", ["Cancelled", "Rescheduled", "Closed", "No Show"]],
			},
			fields=[
				"name",
				"appointment_date",
				"appointment_type",
				"service_provider_name",
				"start_time",
				"end_time",
				"status",
				"total_amount",
				"currency",
			],
			order_by="appointment_date asc, start_time asc",
		)
		appointment_names = [appointment.name for appointment in appointments]
		invoice_map = self.get_appointment_invoice_map(appointment_names)

		guest_rows = frappe.get_all(
			"Service Appointment Guest",
			filters={"parent": ["in", appointment_names]},
			fields=["parent", "full_name", "is_primary"],
			order_by="is_primary desc, idx asc",
		)
		guest_map = {}
		for guest in guest_rows:
			guest_map.setdefault(guest.parent, guest.full_name)

		options = []
		for appointment in appointments:
			invoice = invoice_map.get(appointment.name)
			options.append(
				{
					"name": appointment.name,
					"guest_name": guest_map.get(appointment.name) or "Unspecified Guest",
					"appointment_type": appointment.appointment_type,
					"provider": appointment.service_provider_name,
					"appointment_date": appointment.appointment_date,
					"start_time": appointment.start_time,
					"end_time": appointment.end_time,
					"status": appointment.status,
					"total_amount": appointment.total_amount,
					"currency": appointment.currency or self.currency,
					"sales_invoice": invoice.name if invoice else None,
					"can_invoice": appointment.status == "Completed" and not invoice,
				}
			)

		return {
			"booking_invoice": self.get_linked_sales_invoice(),
			"appointments": options,
		}

	@frappe.whitelist()
	def create_appointment_sales_invoices(self, appointment_names):
		if isinstance(appointment_names, str):
			appointment_names = frappe.parse_json(appointment_names)

		appointment_names = list(dict.fromkeys(appointment_names or []))
		if not appointment_names:
			frappe.throw(_("Select at least one appointment to invoice."))

		existing_booking_invoice = self.get_linked_sales_invoice()
		if existing_booking_invoice:
			frappe.throw(
				_("Sales Invoice {0} already exists for this booking.").format(existing_booking_invoice.name),
				title=_("Already Invoiced"),
			)

		appointments = frappe.get_all(
			"Service Appointment",
			filters={"name": ["in", appointment_names], "booking_id": self.name},
			fields=["name", "status"],
		)
		if len(appointments) != len(appointment_names):
			frappe.throw(_("One or more selected appointments do not belong to this booking."))

		incomplete = [appointment.name for appointment in appointments if appointment.status != "Completed"]
		if incomplete:
			frappe.throw(
				_("Only completed appointments can be invoiced: {0}").format(", ".join(incomplete)),
				title=_("Appointments Not Complete"),
			)

		existing_appointment_invoices = self.get_appointment_invoice_map(appointment_names)
		if existing_appointment_invoices:
			frappe.throw(
				_("Sales Invoices already exist for selected appointments: {0}").format(
					", ".join(sorted(invoice.name for invoice in existing_appointment_invoices.values()))
				),
				title=_("Already Invoiced"),
			)

		created_invoices = []
		for appointment_name in appointment_names:
			appointment = frappe.get_doc("Service Appointment", appointment_name)
			invoice_name = appointment.create_sales_invoice()
			created_invoices.append(
				{
					"appointment": appointment.name,
					"sales_invoice": invoice_name,
				}
			)

		return created_invoices

	@frappe.whitelist()
	def add_guest(self, guest_data: dict):
		if self.docstatus != 0:
			frappe.throw(_("Cannot add guest appointments to a submitted booking."))

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
				"selected_slot_ids": json.dumps(guest_data.get("slot_ids") or []),
				"all_available_providers": json.dumps(guest_data.get("all_available_providers", [])),
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
