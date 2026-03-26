import json

import frappe


@frappe.whitelist()
def create_booking(customer, guests):
	if isinstance(customer, str):
		customer = json.loads(customer)
	if isinstance(guests, str):
		guests = json.loads(guests)

	booking_id = frappe.generate_hash(length=12)

	created_appointments = []

	for guest in guests:
		slot = guest.get("slot") or {}

		appointment = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"booking_id": booking_id,
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
				"total_amount": guest.get("amount"),
				"notes": guest.get("notes"),
				"is_primary": guest.get("is_primary"),
				"source": "Booking Desk",
			}
		)

		appointment.append(
			"guests",
			{
				"full_name": guest.get("guest_full_name"),
				"email": guest.get("guest_email"),
				"mobile_no": guest.get("guest_mobile_no"),
			},
		)

		appointment.insert(ignore_permissions=True)
		created_appointments.append(appointment.name)

	frappe.db.commit()

	return {"booking_id": booking_id, "appointments": created_appointments}
