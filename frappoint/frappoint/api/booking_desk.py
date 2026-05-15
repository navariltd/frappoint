import json
from collections import defaultdict

import frappe


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
