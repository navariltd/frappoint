import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt


def _parse_json_payload(value, fallback):
	if value is None:
		return fallback
	if isinstance(value, str):
		return json.loads(value)
	return value


def _get_price_doc(
	service_type: str,
	price_id: str | None = None,
	amount: float | None = None,
	duration: int | None = None,
	pricing_model: str | None = None,
):
	if price_id:
		price_doc = frappe.get_value(
			"Service Type Price",
			{"parent": service_type, "price_name": price_id},
			["price_name", "pricing_model", "amount", "currency", "duration"],
			as_dict=True,
		)

		if not price_doc:
			frappe.throw(_("Price {0} not found for service {1}.").format(price_id, service_type))

		return price_doc

	price_docs = frappe.get_all(
		"Service Type Price",
		filters={"parent": service_type},
		fields=["price_name", "pricing_model", "amount", "currency", "duration"],
	)

	if not price_docs:
		return None

	candidates = price_docs

	if pricing_model:
		matched = [doc for doc in candidates if doc.pricing_model == pricing_model]
		if matched:
			candidates = matched

	if duration is not None:
		matched = [doc for doc in candidates if (doc.duration or 0) == duration]
		if matched:
			candidates = matched

	if amount is not None:
		matched = [doc for doc in candidates if flt(doc.amount) == flt(amount)]
		if len(matched) == 1:
			return matched[0]
		if len(matched) > 1:
			candidates = matched

	if len(candidates) == 1:
		return candidates[0]

	if amount is not None or duration is not None or pricing_model:
		frappe.throw(_("Could not uniquely resolve the selected price for service {0}.").format(service_type))

	return candidates[0]


def _serialize_booking(booking):
	appointments = frappe.get_all(
		"Service Appointment",
		filters={"booking_id": booking.name, "docstatus": ["!=", 2]},
		fields=[
			"name",
			"appointment_type",
			"appointment_date",
			"start_time",
			"end_time",
			"appointment_provider",
			"status",
			"full_name",
			"email",
			"mobile_no",
			"selected_slot_ids",
		],
		order_by="creation asc",
	)

	return {
		"name": booking.name,
		"status": booking.status,
		"customer": booking.customer,
		"fullName": booking.full_name,
		"email": booking.email,
		"mobileNo": booking.mobile_no,
		"currency": booking.currency,
		"subtotal": booking.subtotal,
		"grandTotal": booking.grand_total,
		"totalGuests": booking.total_guests,
		"items": [
			{
				"serviceType": item.service_type,
				"pricingModel": item.pricing_model,
				"quantity": item.qty,
				"rate": item.rate,
				"totalAmount": item.total_amount,
				"currency": item.currency,
			}
			for item in booking.items
		],
		"appointments": [
			{
				"name": appointment.name,
				"serviceType": appointment.appointment_type,
				"date": appointment.appointment_date,
				"startTime": appointment.start_time,
				"endTime": appointment.end_time,
				"provider": appointment.appointment_provider,
				"status": appointment.status,
				"fullName": appointment.full_name,
				"email": appointment.email,
				"mobileNo": appointment.mobile_no,
				"slotIds": json.loads(appointment.selected_slot_ids) if appointment.selected_slot_ids else [],
			}
			for appointment in appointments
		],
	}


@frappe.whitelist()
def create_draft_service_booking(customer=None, items=None):
	customer = _parse_json_payload(customer, {})
	items = _parse_json_payload(items, [])

	if not customer or not customer.get("customer"):
		frappe.throw(_("Customer is required before continuing the booking."))
	if not items:
		frappe.throw(_("Add at least one service before creating a draft booking."))

	booking = frappe.new_doc("Service Booking")
	booking.customer = customer.get("customer")
	booking.full_name = customer.get("fullName") or customer.get("name")
	booking.email = customer.get("email")
	booking.mobile_no = customer.get("mobileNo")
	booking.booking_date = frappe.utils.today()
	booking.booking_time = frappe.utils.now_datetime()
	booking.status = "Draft"
	booking.currency = items[0].get("currency") or "KES"

	total_guests = 0
	for item in items:
		service_type = item.get("serviceType") or item.get("serviceId")
		quantity = int(item.get("quantity") or 1)
		price_id = item.get("priceId") or item.get("packageId")
		rate = item.get("rate") or item.get("price")
		price_doc = _get_price_doc(
			service_type,
			price_id=price_id,
			amount=rate,
			duration=item.get("duration"),
			pricing_model=item.get("pricingModel"),
		)
		rate = item.get("rate") or item.get("price") or (price_doc.amount if price_doc else 0)
		pricing_model = item.get("pricingModel") or (price_doc.pricing_model if price_doc else "Per Guest")
		currency = item.get("currency") or (price_doc.currency if price_doc else booking.currency)
		total_amount = item.get("totalAmount") or (float(rate) * quantity)

		booking.append(
			"items",
			{
				"service_type": service_type,
				"pricing_model": pricing_model,
				"qty": quantity,
				"currency": currency,
				"rate": rate,
				"total_amount": total_amount,
			},
		)
		total_guests += quantity

	booking.total_guests = total_guests
	booking.insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep

	return _serialize_booking(booking)


@frappe.whitelist()
def upsert_draft_service_appointment(booking_id: str, assignment=None, appointment_id: str | None = None):
	assignment = _parse_json_payload(assignment, {})
	if not booking_id:
		frappe.throw(_("Booking reference is required to reserve an appointment."))

	booking = frappe.get_doc("Service Booking", booking_id)
	service_type = assignment.get("serviceType") or assignment.get("serviceId")
	guest = assignment.get("guest") or {}
	slot = assignment.get("slot") or {}
	service_item = assignment.get("service") or {}
	service_payload = {**assignment, **service_item}

	if not service_type:
		frappe.throw(_("Service type is required to create an appointment."))
	if not guest.get("fullName"):
		frappe.throw(_("Guest full name is required before reserving a slot."))
	if not assignment.get("date"):
		frappe.throw(_("Appointment date is required before reserving a slot."))
	if not slot.get("startTime") or not slot.get("endTime"):
		frappe.throw(_("Selected slot is incomplete."))
	if not slot.get("provider"):
		frappe.throw(_("Provider is required for slot reservation."))

	price_id = service_payload.get("priceId") or service_payload.get("packageId")
	amount = service_payload.get("price")
	price_doc = _get_price_doc(
		service_type,
		price_id=price_id,
		amount=amount,
		duration=service_payload.get("duration"),
		pricing_model=service_payload.get("pricingModel"),
	)
	amount = service_payload.get("price") or (price_doc.amount if price_doc else 0)
	currency = service_payload.get("currency") or (price_doc.currency if price_doc else booking.currency)
	duration = service_payload.get("duration") or (price_doc.duration if price_doc else None)
	resolved_price_name = price_id or (price_doc.price_name if price_doc else None)

	if appointment_id:
		appointment = frappe.get_doc("Service Appointment", appointment_id)
		if appointment.booking_id != booking.name:
			frappe.throw(
				_("Appointment {0} does not belong to booking {1}.").format(appointment_id, booking.name)
			)
	else:
		appointment = frappe.new_doc("Service Appointment")
		appointment.booking_id = booking.name
		appointment.source = "Booking Desk"
		appointment.status = "Open"

	appointment.customer = booking.customer
	appointment.appointment_type = service_type
	appointment.appointment_date = assignment.get("date")
	appointment.appointment_provider = slot.get("provider")
	appointment.duration = duration
	appointment.appointment_price = resolved_price_name
	appointment.currency = currency
	appointment.start_time = slot.get("startTime")
	appointment.end_time = slot.get("endTime")
	appointment.selected_slot_ids = json.dumps(slot.get("slotIds") or [])
	appointment.all_available_providers = json.dumps(slot.get("providers") or [])
	appointment.full_name = guest.get("fullName")
	appointment.email = guest.get("email") or booking.email
	appointment.mobile_no = guest.get("mobileNo") or booking.mobile_no
	appointment.total_amount = amount
	appointment.notes = guest.get("notes")

	appointment.set("guests", [])
	appointment.append(
		"guests",
		{
			"full_name": guest.get("fullName"),
			"email": guest.get("email") or booking.email,
			"mobile_no": guest.get("mobileNo") or booking.mobile_no,
			"is_primary": 1,
			"notes": guest.get("notes"),
		},
	)

	if appointment.is_new():
		appointment.insert(ignore_permissions=True)
	else:
		appointment.save(ignore_permissions=True)

	booking.reload()
	booking.sync_financial_snapshot()
	frappe.db.commit()  # nosemgrep

	return {
		"booking": _serialize_booking(booking),
		"appointment": {
			"name": appointment.name,
			"bookingId": appointment.booking_id,
			"serviceType": appointment.appointment_type,
			"date": appointment.appointment_date,
			"startTime": appointment.start_time,
			"endTime": appointment.end_time,
			"provider": appointment.appointment_provider,
			"status": appointment.status,
			"fullName": appointment.full_name,
			"email": appointment.email,
			"mobileNo": appointment.mobile_no,
			"slotIds": json.loads(appointment.selected_slot_ids) if appointment.selected_slot_ids else [],
		},
	}


@frappe.whitelist()
def get_draft_service_booking(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	booking = frappe.get_doc("Service Booking", booking_id)
	return _serialize_booking(booking)


@frappe.whitelist()
def create_booking(customer: str, guests: list):
	if isinstance(customer, str):
		customer = json.loads(customer)
	if isinstance(guests, str):
		guests = json.loads(guests)

	booking = frappe.new_doc("Service Booking")
	booking.customer = customer.get("customer")
	booking.full_name = customer.get("fullName")
	booking.email = customer.get("email")
	booking.mobile_no = customer.get("mobileNo")
	booking.booking_date = frappe.utils.today()
	booking.status = "Draft"
	booking.currency = guests[0].get("currency")

	booking.insert(ignore_permissions=True)

	grouped_data = defaultdict(list)
	for guest in guests:
		grouped_data[guest.get("appointment_type")].append(guest)

	total_subtotal = 0
	service_price_map = {}

	created_appointments = []

	for service_type, guest_list in grouped_data.items():
		count = len(guest_list)

		price_id = guest_list[0].get("price_id")
		price_doc = frappe.get_value(
			"Service Type Price",
			{"price_name": price_id, "parent": service_type},
			["pricing_model", "amount", "currency"],
			as_dict=True,
		)

		if not price_doc:
			frappe.throw(f"Price '{price_id}' not found for {service_type}")

		pricing_model = price_doc.pricing_model or "Per Guest"
		base_rate = price_doc.amount or 0

		line_total = 0
		individual_appt_amount = 0

		if pricing_model == "Per Guest":
			line_total = base_rate * count
			individual_appt_amount = base_rate
		else:
			line_total = base_rate
			individual_appt_amount = base_rate / count

		service_price_map[service_type] = individual_appt_amount

		booking.append(
			"items",
			{
				"service_type": service_type,
				"pricing_model": pricing_model,
				"qty": count,
				"currency": booking.currency,
				"rate": base_rate,
				"total_amount": line_total,
			},
		)
		total_subtotal += line_total

	booking.subtotal = total_subtotal
	booking.grand_total = total_subtotal
	booking.total_guests = len(guests)
	booking.save(ignore_permissions=True)

	for guest in guests:
		slot = guest.get("slot") or {}
		guest_service_type = guest.get("appointment_type")
		calculated_amount = service_price_map.get(guest_service_type, 0)

		appointment = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"booking_id": booking.name,
				"appointment_type": guest_service_type,
				"appointment_date": guest.get("date"),
				"appointment_provider": slot.get("provider"),
				"duration": guest.get("duration"),
				"appointment_price": guest.get("price_id"),
				"currency": guest.get("currency"),
				"start_time": slot.get("start_time"),
				"end_time": slot.get("end_time"),
				"selected_slot_ids": json.dumps(slot.get("slot_ids", [])),
				"customer": customer.get("customer"),
				"full_name": guest.get("guest_full_name")
				or guest.get("full_name")
				or customer.get("fullName"),
				"email": guest.get("guest_email") or guest.get("email") or customer.get("email"),
				"mobile_no": guest.get("guest_mobile_no")
				or guest.get("mobile_no")
				or customer.get("mobileNo"),
				"total_amount": calculated_amount,
				"notes": guest.get("notes"),
				"source": "Booking Desk",
			}
		)

		appointment.append(
			"guests",
			{
				"full_name": guest.get("guest_full_name")
				or guest.get("full_name")
				or customer.get("fullName"),
				"email": guest.get("guest_email") or guest.get("email") or customer.get("email"),
				"mobile_no": guest.get("guest_mobile_no")
				or guest.get("mobile_no")
				or customer.get("mobileNo"),
				"is_primary": guest.get("is_primary", 1),
			},
		)

		appointment.insert(ignore_permissions=True)
		created_appointments.append(appointment.name)

	frappe.db.commit()  # nosemgrep

	return {
		"booking_id": booking.name,
		"appointments": created_appointments,
		"grand_total": booking.grand_total,
	}
