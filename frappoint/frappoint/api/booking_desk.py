import json
from collections import defaultdict

import frappe


@frappe.whitelist()
def add_guest_to_booking(booking_id, guest_data):
	if isinstance(guest_data, str):
		guest_data = frappe.parse_json(guest_data)

	booking = frappe.get_doc("Service Booking", booking_id)
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
			"booking_id": booking.name,
			"appointment_type": service_type,
			"appointment_date": guest_data.get("date"),
			"appointment_provider": guest_data.get("provider"),
			"duration": price_doc.duration,
			"appointment_price": price_id,
			"currency": price_doc.currency,
			"start_time": guest_data.get("start_time"),
			"end_time": guest_data.get("end_time"),
			"selected_slot_ids": json.dumps(guest_data.get("slot_ids", [])),
			"customer": booking.customer,
			# top-level fields
			"total_amount": price_doc.amount,
			"source": "Booking Desk",
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
	booking.append(
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

	booking.save(ignore_permissions=True)

	return {"appointment": appointment.name, "grand_total": booking.grand_total}


@frappe.whitelist()
def create_booking(customer, guests):
	if isinstance(customer, str):
		customer = json.loads(customer)
	if isinstance(guests, str):
		guests = json.loads(guests)

	booking = frappe.new_doc("Service Booking")
	booking.customer = customer.get("customer")
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
		calculated_amount = service_price_map.get(service_type, 0)

		appointment = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"booking_id": booking.name,
				"appointment_type": guest.get("appointment_type"),
				"appointment_date": guest.get("date"),
				"appointment_provider": slot.get("provider"),
				"duration": guest.get("duration"),
				"appointment_price": guest.get("price_id"),
				"currency": guest.get("currency"),
				"start_time": slot.get("start_time"),
				"end_time": slot.get("end_time"),
				"selected_slot_ids": json.dumps(slot.get("slot_ids", [])),
				"customer": customer.get("customer"),
				"customer_name": customer.get("fullName"),
				"customer_email": customer.get("email"),
				"customer_mobile": customer.get("mobileNo"),
				"total_amount": calculated_amount,
				"notes": guest.get("notes"),
				"source": "Booking Desk",
			}
		)

		appointment.append(
			"guests",
			{
				"full_name": guest.get("guest_full_name"),
				"email": guest.get("guest_email"),
				"mobile_no": guest.get("guest_mobile_no"),
				"is_primary": guest.get("is_primary"),
			},
		)

		appointment.insert(ignore_permissions=True)
		created_appointments.append(appointment.name)

	frappe.db.commit()

	return {
		"booking_id": booking.name,
		"appointments": created_appointments,
		"grand_total": booking.grand_total,
	}
