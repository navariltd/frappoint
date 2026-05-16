import json

import frappe
from frappe import _


@frappe.whitelist()
def create_booking_with_appointments(booking_payload=None):
	"""Create a Service Booking and linked Service Appointment(s).

	Accepts either a JSON string or dict with keys:
	  - customer (object or string)
	  - currency
	  - items or guests: list of appointment snapshots

	Returns: { booking_id, appointments: [names], grand_total }
	"""
	if not booking_payload:
		frappe.throw(_("Missing booking_payload"))

	try:
		data = json.loads(booking_payload) if isinstance(booking_payload, str) else booking_payload
	except Exception:
		data = booking_payload

	data = frappe._dict(data or {})

	# Accept either `items` or the legacy `guests` payload key
	items = data.get("items") or data.get("guests") or []
	if not items:
		frappe.throw(_("Booking must include at least one appointment/item."))

	# Build booking doc
	booking = frappe.get_doc(
		{
			"doctype": "Service Booking",
			"customer": (
				data.get("customer")
				if not isinstance(data.get("customer"), dict)
				else data.get("customer").get("customer") or data.get("customer").get("customer_id")
			),
			"full_name": data.get("full_name")
			or (data.get("customer") and data.get("customer").get("fullName")),
			"email": data.get("email") or (data.get("customer") and data.get("customer").get("email")),
			"mobile_no": data.get("mobile_no")
			or (data.get("customer") and data.get("customer").get("mobileNo")),
			"currency": data.get("currency") or "USD",
			"items": [],
			"source": "Portal",
		}
	)

	for it in items:
		it = frappe._dict(it or {})
		booking.append(
			"items",
			{
				"service_type": it.get("service_type") or it.get("appointment_type"),
				"price_id": it.get("price_id") or it.get("price_name") or it.get("appointment_price"),
				"qty": it.get("qty", 1),
				"total_amount": it.get("amount") or it.get("price") or it.get("total_amount") or 0,
				"currency": it.get("currency") or data.get("currency"),
			},
		)

	booking.insert(ignore_permissions=True)

	created = []
	for it in items:
		try:
			it = frappe._dict(it or {})
			appt = frappe.get_doc(
				{
					"doctype": "Service Appointment",
					"booking_id": booking.name,
					"appointment_type": it.get("service_type") or it.get("appointment_type"),
					"appointment_date": it.get("date"),
					"start_time": it.get("start_time")
					or (it.get("slot") and it.get("slot").get("start_time")),
					"end_time": it.get("end_time") or (it.get("slot") and it.get("slot").get("end_time")),
					"appointment_price": it.get("price_id")
					or it.get("price_name")
					or it.get("appointment_price"),
					"total_amount": it.get("amount") or it.get("price") or it.get("total_amount") or 0,
					"currency": it.get("currency") or data.get("currency"),
					"appointment_provider": it.get("provider"),
					"customer": (
						data.get("customer")
						if not isinstance(data.get("customer"), dict)
						else data.get("customer").get("customer")
					),
					"source": "Portal",
					"status": it.get("status") or "Open",
				}
			)

			# selected_slot_ids if present in slot or slot_ids
			try:
				slot = it.get("slot") or {}
				slot_ids = slot.get("slot_ids") if isinstance(slot, dict) else None
				if slot_ids:
					appt.set("selected_slot_ids", json.dumps(slot_ids))
				elif it.get("slot_ids"):
					appt.set("selected_slot_ids", json.dumps(it.get("slot_ids")))
			except Exception:
				pass

			# add guest entry if present
			guest_name = it.get("guest_name") or it.get("guest_full_name") or data.get("full_name")
			guest_email = it.get("guest_email") or it.get("guest_email") or data.get("email")
			guest_mobile = it.get("guest_mobile") or it.get("guest_mobile") or data.get("mobile_no")
			if guest_name or guest_email or guest_mobile:
				appt.append(
					"guests",
					{
						"full_name": guest_name or "",
						"email": guest_email or "",
						"mobile_no": guest_mobile or "",
						"is_primary": 1,
						"notes": it.get("notes") or "",
					},
				)

			appt.insert(ignore_permissions=True)
			created.append(appt.name)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				"create_booking_with_appointments: appointment creation failed",
			)

	# Recalculate booking totals and persist
	try:
		booking.recalculate_totals()
		booking.save(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"create_booking_with_appointments: booking recalc failed",
		)

	return {
		"booking_id": booking.name,
		"appointments": created,
		"grand_total": getattr(booking, "grand_total", 0),
	}
