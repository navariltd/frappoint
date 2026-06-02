import json

import frappe
from frappe import _
from frappe.utils import flt

from frappoint.frappoint.services.pricing_service import calculate_booking_pricing


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

	def _first(*values):
		for value in values:
			if value is not None and value != "":
				return value
		return None

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
		service_type = _first(it.get("service_type"), it.get("serviceType"), it.get("appointment_type"))
		price_id = _first(
			it.get("price_id"),
			it.get("priceId"),
			it.get("price_name"),
			it.get("appointment_price"),
		)
		total_amount = _first(it.get("amount"), it.get("price"), it.get("total_amount"), 0)
		booking.append(
			"items",
			{
				"service_type": service_type,
				"price_id": price_id,
				"qty": it.get("qty", 1),
				"total_amount": total_amount,
				"currency": it.get("currency") or data.get("currency"),
			},
		)

	booking.insert(ignore_permissions=True)

	created = []
	for it in items:
		try:
			it = frappe._dict(it or {})
			slot = frappe._dict(it.get("slot") or {})
			provider = _first(it.get("provider"), slot.get("provider"))
			service_unit = _first(
				it.get("service_unit"),
				it.get("serviceUnit"),
				slot.get("service_unit"),
				slot.get("serviceUnit"),
			)
			start_time = _first(
				it.get("start_time"), it.get("startTime"), slot.get("start_time"), slot.get("startTime")
			)
			end_time = _first(
				it.get("end_time"), it.get("endTime"), slot.get("end_time"), slot.get("endTime")
			)
			slot_ids = (
				_first(slot.get("slot_ids"), slot.get("slotIds"), it.get("slot_ids"), it.get("slotIds")) or []
			)
			appt = frappe.get_doc(
				{
					"doctype": "Service Appointment",
					"booking_id": booking.name,
					"appointment_type": _first(
						it.get("service_type"), it.get("serviceType"), it.get("appointment_type")
					),
					"appointment_date": _first(
						it.get("date"), it.get("appointment_date"), it.get("appointmentDate")
					),
					"start_time": start_time,
					"end_time": end_time,
					"appointment_price": _first(
						it.get("price_id"),
						it.get("priceId"),
						it.get("price_name"),
						it.get("appointment_price"),
					),
					"total_amount": _first(it.get("amount"), it.get("price"), it.get("total_amount"), 0),
					"currency": it.get("currency") or data.get("currency"),
					"appointment_provider": provider,
					"service_unit": service_unit,
					"customer": (
						data.get("customer")
						if not isinstance(data.get("customer"), dict)
						else data.get("customer").get("customer")
					),
					"source": "Portal",
					"status": it.get("status") or "Open",
				}
			)

			# selected_slot_ids are optional in allocation-first flows.
			try:
				if slot_ids:
					appt.set("selected_slot_ids", json.dumps(slot_ids))
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


@frappe.whitelist()
def get_booking_pricing_summary(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	pricing = calculate_booking_pricing(booking)

	return {
		"bookingId": booking.name,
		"currency": booking.currency,
		"subtotal": flt(pricing.get("subtotalAmount") or 0),
		"appointmentDiscountTotal": flt(pricing.get("appointmentDiscountTotal") or 0),
		"bookingDiscountAmount": flt(pricing.get("bookingDiscountAmount") or 0),
		"intermediateTotal": flt(pricing.get("intermediateTotal") or 0),
		"finalAmount": flt(pricing.get("finalAmount") or 0),
		"coupon": {
			"code": booking.coupon_code or "",
			"applied": bool(booking.coupon_applied),
			"discountType": booking.coupon_discount_type or "",
			"discountAmount": flt(booking.coupon_discount_amount or 0),
			"scope": booking.coupon_scope or "",
			"validationMessage": pricing.get("bookingCouponMessage") or "",
			"isValid": bool(pricing.get("bookingCoupon")),
		},
		"appointmentBreakdown": pricing.get("appointmentBreakdown") or [],
		"appointmentCoupons": pricing.get("appointmentCoupons") or [],
	}
