import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder.functions import Max
from frappe.utils import cint, flt, get_datetime, get_time, getdate, now_datetime
from frappe.utils.user import is_website_user

from frappoint.frappoint.doctype.service_appointment.service_appointment import (
	cancel_appointment,
	reschedule_appointment,
)
from frappoint.frappoint.doctype.service_appointment_event_log.service_appointment_event_log import (
	apply_appointment_event_action,
	compute_appointment_time_summary,
	get_appointment_event_logs,
)
from frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	change_appointment_provider,
)
from frappoint.frappoint.services.availability_projector import (
	get_available_slots as get_projected_available_slots,
)
from frappoint.frappoint.services.availability_projector import (
	get_couple_available_slots as get_projected_couple_available_slots,
)
from frappoint.frappoint.services.ongoing_provider_reassignment_service import (
	get_ongoing_reassignment_options,
	reassign_ongoing_appointment,
)
from frappoint.frappoint.services.pricing_service import (
	calculate_booking_pricing,
	coupon_scope_label,
	is_booking_level_coupon,
	resolve_coupon_doc,
)
from frappoint.frappoint.services.provider_assignment_service import (
	rank_provider_options,
	select_provider_for_assignment,
	throw_no_provider_available,
)
from frappoint.payments import (
	get_confirmation_deposit_percent,
	get_payment_amount,
	get_payment_gateways_for_service_type,
	get_payment_link,
)


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


def _serialize_booking(booking, pricing=None):
	pricing = pricing or calculate_booking_pricing(booking)
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
			"service_provider_name",
			"status",
			"payment_status",
			"total_amount",
			"outstanding_amount",
			"coupon_code",
			"discount_amount",
			"grand_total",
			"full_name",
			"email",
			"mobile_no",
			"notes",
			"couple_appointment_id",
			"is_primary_in_couple",
			"selected_slot_ids",
		],
		order_by="creation asc",
	)
	provider_ids = [row.appointment_provider for row in appointments if row.get("appointment_provider")]
	provider_names = _get_provider_name_map(provider_ids)
	is_couple = bool(cint(getattr(booking, "is_couple", 0))) or any(
		bool(row.couple_appointment_id) for row in appointments
	)

	return {
		"name": booking.name,
		"isCouple": is_couple,
		"status": booking.status,
		"customer": booking.customer,
		"fullName": booking.full_name,
		"email": booking.email,
		"mobileNo": booking.mobile_no,
		"bookedBy": booking.booked_by,
		"currency": booking.currency,
		"subtotal": booking.subtotal,
		"subtotalAmount": flt(pricing.get("subtotalAmount") or booking.subtotal),
		"appointmentDiscountTotal": flt(
			booking.appointment_discount_total or pricing.get("appointmentDiscountTotal") or 0
		),
		"bookingDiscountAmount": flt(
			booking.booking_discount_amount or pricing.get("bookingDiscountAmount") or 0
		),
		"totalAmount": flt(pricing.get("totalAmount") or booking.grand_total),
		"finalAmount": flt(pricing.get("finalAmount") or booking.grand_total),
		"couponCode": booking.coupon_code,
		"couponDiscountType": booking.coupon_discount_type,
		"couponDiscountAmount": flt(booking.coupon_discount_amount or 0),
		"couponScope": booking.coupon_scope,
		"grandTotal": booking.grand_total,
		"outstandingAmount": booking.outstanding_amount,
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
				"provider": appointment.service_provider_name
				or provider_names.get(appointment.appointment_provider)
				or appointment.appointment_provider,
				"providerId": appointment.appointment_provider,
				"serviceProviderName": appointment.service_provider_name,
				"status": appointment.status,
				"paymentStatus": appointment.payment_status,
				"totalAmount": appointment.total_amount,
				"grandTotal": appointment.grand_total,
				"discountAmount": appointment.discount_amount,
				"couponCode": appointment.coupon_code,
				"outstandingAmount": appointment.outstanding_amount,
				"fullName": appointment.full_name,
				"email": appointment.email,
				"mobileNo": appointment.mobile_no,
				"notes": appointment.notes,
				"slotIds": _safe_json_loads(appointment.selected_slot_ids, []),
				"isCouple": bool(appointment.couple_appointment_id),
				"coupleAppointmentId": appointment.couple_appointment_id,
				"isPrimaryInCouple": bool(appointment.is_primary_in_couple),
			}
			for appointment in appointments
		],
		"pricing": {
			"subtotalAmount": flt(pricing.get("subtotalAmount") or 0),
			"appointmentDiscountTotal": flt(pricing.get("appointmentDiscountTotal") or 0),
			"bookingDiscountAmount": flt(pricing.get("bookingDiscountAmount") or 0),
			"totalAmount": flt(pricing.get("totalAmount") or 0),
			"finalAmount": flt(pricing.get("finalAmount") or 0),
			"intermediateTotal": flt(pricing.get("intermediateTotal") or 0),
			"appointmentBreakdown": pricing.get("appointmentBreakdown") or [],
			"bookingCoupon": pricing.get("bookingCoupon"),
			"appointmentCoupons": pricing.get("appointmentCoupons") or [],
		},
	}


def _safe_json_loads(value, fallback):
	if value is None:
		return fallback
	if isinstance(value, str):
		try:
			return json.loads(value)
		except Exception:
			return fallback
	return value


def _get_provider_name_map(provider_ids):
	provider_ids = sorted({provider for provider in provider_ids if provider})
	if not provider_ids:
		return {}

	return {
		row["name"]: row["provider_name"] or row["name"]
		for row in frappe.get_all(
			"Service Provider",
			filters={"name": ["in", provider_ids]},
			fields=["name", "provider_name"],
		)
	}


def _serialize_appointment(appointment):
	return {
		"name": appointment.name,
		"appointmentId": appointment.name,
		"docstatus": appointment.docstatus,
		"bookingId": appointment.booking_id,
		"isCouple": bool(getattr(appointment, "couple_appointment_id", None)),
		"coupleAppointmentId": getattr(appointment, "couple_appointment_id", None),
		"isPrimaryInCouple": bool(getattr(appointment, "is_primary_in_couple", 0)),
		"status": appointment.status,
		"paymentStatus": appointment.payment_status,
		"customer": appointment.customer,
		"customerName": appointment.customer,
		"fullName": appointment.full_name,
		"email": appointment.email,
		"mobileNo": appointment.mobile_no,
		"currency": appointment.currency,
		"appointmentType": appointment.appointment_type,
		"appointmentDate": appointment.appointment_date,
		"startTime": appointment.start_time,
		"endTime": appointment.end_time,
		"checkedInAt": getattr(appointment, "checked_in_at", None),
		"startedAt": getattr(appointment, "started_at", None),
		"completedAt": getattr(appointment, "completed_at", None),
		"actualStartTime": appointment.actual_start_time,
		"actualEndTime": appointment.actual_end_time,
		"duration": appointment.duration,
		"serviceUnit": appointment.service_unit,
		"provider": appointment.service_provider_name
		or _get_provider_name_map([appointment.appointment_provider]).get(appointment.appointment_provider)
		or appointment.appointment_provider,
		"providerId": appointment.appointment_provider,
		"serviceProviderName": appointment.service_provider_name,
		"appointmentPrice": appointment.appointment_price,
		"totalAmount": flt(appointment.total_amount),
		"discountAmount": flt(appointment.get_discount_amount_for_outstanding()),
		"grandTotal": flt(appointment.grand_total or appointment.total_amount),
		"outstandingAmount": flt(appointment.outstanding_amount),
		"details": appointment.details,
		"notes": appointment.notes,
		"source": appointment.source,
		"selectedSlotIds": _safe_json_loads(getattr(appointment, "selected_slot_ids", None), []),
		"allAvailableProviders": _safe_json_loads(getattr(appointment, "all_available_providers", None), []),
		"modified": appointment.modified,
		"creation": appointment.creation,
	}


def _serialize_appointment_event_log(log):
	return {
		"name": log.get("name"),
		"appointment": log.get("appointment"),
		"booking": log.get("booking"),
		"logType": log.get("logType"),
		"startTime": log.get("startTime"),
		"endTime": log.get("endTime"),
		"durationSeconds": int(log.get("durationSeconds") or 0),
		"createdBy": log.get("createdBy"),
		"notes": log.get("notes") or "",
	}


def _serialize_appointment_payment(payment):
	return {
		"name": payment.name,
		"referenceDoctype": payment.reference_doctype,
		"referenceDocname": payment.reference_docname,
		"user": payment.user,
		"modeOfPayment": payment.mode_of_payment,
		"paymentGateway": payment.payment_gateway,
		"postingDate": payment.posting_date,
		"referenceDate": payment.reference_date,
		"paymentReceived": payment.payment_received,
		"currency": payment.currency,
		"amount": flt(payment.amount),
		"paymentId": payment.payment_id,
		"orderId": payment.order_id,
		"modified": payment.modified,
	}


def _time_key(value):
	if value is None:
		return ""
	return str(value).split(".")[0]


def _get_allocation_provider_change_options(appointment):
	if not appointment.appointment_type or not appointment.appointment_date:
		return []

	rows = get_projected_available_slots(
		service_type_id=appointment.appointment_type,
		start_date=appointment.appointment_date,
		end_date=appointment.appointment_date,
		required_duration_minutes=appointment.duration,
	)
	if not rows:
		return []

	target_start = _time_key(appointment.start_time)
	target_end = _time_key(appointment.end_time)
	seen = set()
	options = []

	for row in rows:
		provider = row.get("provider")
		if not provider or provider == appointment.appointment_provider:
			continue

		if _time_key(row.get("start_time")) != target_start:
			continue
		if _time_key(row.get("end_time")) != target_end:
			continue

		service_unit = row.get("service_unit")
		provider_key = (provider, service_unit or "")
		if provider_key in seen:
			continue
		seen.add(provider_key)

		options.append(
			{
				"provider": provider,
				"provider_name": row.get("provider_name") or provider,
				"service_unit": service_unit,
				"service_unit_name": row.get("service_unit_name") or service_unit,
				"slot_ids": row.get("slot_ids") or [],
			}
		)

	return rank_provider_options(
		options,
		appointment_date=appointment.appointment_date,
		service_type=appointment.appointment_type,
		exclude_provider=appointment.appointment_provider,
	)


def _build_appointment_timeline(appointment, payments, event_logs):
	timeline = [
		{
			"id": "created",
			"label": "Appointment created",
			"detail": appointment.creation,
			"tone": "info",
			"timestamp": appointment.creation,
		}
	]

	if appointment.booking_id:
		timeline.append(
			{
				"id": "booking-linked",
				"label": "Linked to booking",
				"detail": appointment.booking_id,
				"tone": "neutral",
				"timestamp": appointment.modified,
			}
		)

	if appointment.appointment_provider:
		timeline.append(
			{
				"id": "provider-assigned",
				"label": "Provider assigned",
				"detail": appointment.appointment_provider,
				"tone": "success",
				"timestamp": appointment.modified,
			}
		)

	for event in event_logs:
		timeline.append(
			{
				"id": f"event-{event.get('name')}",
				"label": event.get("logType") or "Activity",
				"detail": event.get("notes") or event.get("startTime") or "",
				"tone": "warning" if event.get("logType") == "Pause" else "success",
				"timestamp": event.get("startTime"),
			}
		)

	for payment in payments:
		if flt(payment.amount) <= 0:
			continue
		timeline.append(
			{
				"id": f"payment-{payment.name}",
				"label": "Payment recorded",
				"detail": f"{payment.currency} {flt(payment.amount):.2f}",
				"tone": "success" if payment.payment_received else "warning",
				"timestamp": payment.modified,
			}
		)

	if appointment.status == "Rescheduled" and appointment.rescheduled_to:
		timeline.append(
			{
				"id": "rescheduled",
				"label": "Appointment rescheduled",
				"detail": appointment.rescheduled_to,
				"tone": "warning",
				"timestamp": appointment.modified,
			}
		)

	if appointment.status == "Cancelled":
		timeline.append(
			{
				"id": "cancelled",
				"label": "Appointment cancelled",
				"detail": appointment.modified,
				"tone": "danger",
				"timestamp": appointment.modified,
			}
		)

	return timeline


def _build_appointment_alerts(appointment, payments):
	alerts = []
	outstanding = flt(appointment.outstanding_amount)

	if appointment.status in ["Open", "Pending Payment"] and outstanding > 0:
		alerts.append(
			{
				"id": "outstanding-payment",
				"severity": "warning",
				"label": "Outstanding balance",
				"message": f"{appointment.currency} {outstanding:.2f} remains unpaid.",
			}
		)

	if not appointment.appointment_provider:
		alerts.append(
			{
				"id": "missing-provider",
				"severity": "warning",
				"label": "Provider not assigned",
				"message": "Assign a provider before the appointment starts.",
			}
		)

	if appointment.status == "Rescheduled":
		alerts.append(
			{
				"id": "rescheduled",
				"severity": "info",
				"label": "Appointment rescheduled",
				"message": "This appointment has been moved to a new time slot.",
			}
		)

	paid_amount = sum(flt(payment.amount) for payment in payments if payment.payment_received)
	if paid_amount > 0 and outstanding <= 0:
		alerts.append(
			{
				"id": "paid",
				"severity": "success",
				"label": "Payment complete",
				"message": f"{appointment.currency} {paid_amount:.2f} has been recorded.",
			}
		)

	return alerts


def _build_appointment_response(appointment, booking=None):
	event_logs = [
		_serialize_appointment_event_log(log) for log in get_appointment_event_logs(appointment.name)
	]
	time_tracking = compute_appointment_time_summary(event_logs)
	payment_rows = frappe.get_all(
		"Service Appointment Payment",
		filters={
			"reference_doctype": "Service Appointment",
			"reference_docname": appointment.name,
		},
		fields=[
			"name",
			"reference_doctype",
			"reference_docname",
			"user",
			"mode_of_payment",
			"payment_gateway",
			"posting_date",
			"reference_date",
			"payment_received",
			"currency",
			"amount",
			"payment_id",
			"order_id",
			"modified",
		],
		order_by="posting_date desc, modified desc",
	)
	payments = [
		_serialize_appointment_payment(frappe.get_doc("Service Appointment Payment", row.name))
		for row in payment_rows
	]
	appointment_payload = _serialize_appointment(appointment)
	direct_paid_amount = sum(
		flt(payment.get("amount")) for payment in payments if payment.get("paymentReceived")
	)
	outstanding_amount = flt(appointment_payload.get("outstandingAmount"))
	discount_amount = flt(appointment_payload.get("discountAmount"))
	final_amount = max(0, flt(appointment_payload.get("totalAmount")) - discount_amount)
	paid_amount = max(direct_paid_amount, final_amount - outstanding_amount)
	if outstanding_amount <= 0 and flt(appointment_payload.get("totalAmount")) > 0:
		payment_status = "Paid"
	elif paid_amount > 0:
		payment_status = "Partly Paid"
	else:
		payment_status = appointment_payload.get("paymentStatus") or "Unpaid"

	appointment_payload["paymentStatus"] = payment_status
	linked_couple_appointment = None
	if getattr(appointment, "couple_appointment_id", None) and frappe.db.exists(
		"Service Appointment", appointment.couple_appointment_id
	):
		linked_couple_appointment = _serialize_appointment(
			frappe.get_doc("Service Appointment", appointment.couple_appointment_id)
		)

	return {
		"appointment": appointment_payload,
		"coupleAppointment": linked_couple_appointment,
		"booking": _serialize_booking(booking) if booking else None,
		"eventLogs": event_logs,
		"timeTracking": time_tracking,
		"payments": payments,
		"paymentSummary": {
			"currency": appointment_payload.get("currency") or (booking.currency if booking else "KES"),
			"totalAmount": flt(appointment_payload.get("totalAmount")),
			"discountAmount": discount_amount,
			"finalAmount": final_amount,
			"paidAmount": paid_amount,
			"outstandingAmount": outstanding_amount,
		},
		"timeline": _build_appointment_timeline(appointment, payment_rows, event_logs),
		"alerts": _build_appointment_alerts(appointment, payment_rows),
		"availability": {
			"serviceType": appointment.appointment_type,
			"duration": appointment.duration,
			"provider": appointment.appointment_provider,
			"date": appointment.appointment_date,
		},
		"actions": {
			"canCheckIn": appointment.status in ["Open", "Pending Payment", "Confirmed"],
			"canStart": (appointment.status in ["Open", "Pending Payment", "Confirmed", "Checked In"])
			and not time_tracking.get("activeSession"),
			"canPause": bool(time_tracking.get("isRunning")),
			"canResume": bool(time_tracking.get("isPaused")),
			"canComplete": appointment.status
			in ["Confirmed", "Open", "Pending Payment", "Checked In", "In Progress"]
			and appointment.status not in ["Completed", "Cancelled", "Closed", "No Show"],
			"canReschedule": appointment.status in ["Open", "Pending Payment", "Confirmed", "Checked In"]
			and appointment.status not in ["Completed", "Cancelled", "Closed", "No Show"],
			"canCancel": appointment.status not in ["Cancelled", "Closed", "Completed", "No Show"],
			"canReassignProvider": appointment.status
			in ["Open", "Pending Payment", "Confirmed", "Checked In", "In Progress"]
			and appointment.status not in ["Completed", "Cancelled", "Closed", "No Show"],
			"canEditTimeSlot": appointment.status in ["Open", "Pending Payment", "Confirmed", "Checked In"]
			and appointment.status not in ["Completed", "Cancelled", "Closed", "No Show"],
		},
	}


def _build_checkout_summary(booking):
	pricing = calculate_booking_pricing(booking)
	total_amount = flt(pricing.get("finalAmount") or booking.grand_total)
	outstanding_amount = max(0, flt(booking.outstanding_amount))
	paid_amount = max(0, total_amount - outstanding_amount)
	deposit_percent = flt(get_confirmation_deposit_percent("Service Booking", booking.name, doc=booking))
	minimum_due = flt(get_payment_amount("Service Booking", booking.name, total_amount, doc=booking))
	coupon_summary = _build_booking_coupon_summary(booking, pricing=pricing)
	can_confirm_without_payment = _can_confirm_checkout_without_payment(booking.name)

	return {
		"booking": _serialize_booking(booking, pricing=pricing),
		"pricing": {
			"subtotalAmount": flt(pricing.get("subtotalAmount") or 0),
			"appointmentDiscountTotal": flt(pricing.get("appointmentDiscountTotal") or 0),
			"bookingDiscountAmount": flt(pricing.get("bookingDiscountAmount") or 0),
			"totalAmount": flt(pricing.get("totalAmount") or 0),
			"finalAmount": flt(pricing.get("finalAmount") or 0),
			"intermediateTotal": flt(pricing.get("intermediateTotal") or 0),
			"appointmentBreakdown": pricing.get("appointmentBreakdown") or [],
			"bookingCoupon": pricing.get("bookingCoupon"),
			"appointmentCoupons": pricing.get("appointmentCoupons") or [],
		},
		"payment": {
			"referenceDoctype": "Service Booking",
			"referenceDocname": booking.name,
			"currency": booking.currency,
			"totalAmount": total_amount,
			"paidAmount": paid_amount,
			"outstandingAmount": outstanding_amount,
			"minimumDue": minimum_due,
			"depositPercent": deposit_percent,
			"totalDiscount": coupon_summary.get("totalDiscount", 0),
			"canConfirmWithoutPayment": can_confirm_without_payment,
		},
		"coupon": coupon_summary,
	}


def _can_confirm_checkout_without_payment(booking_id: str) -> bool:
	settings = frappe.get_cached_doc("Service Appointment Settings")
	if not settings.enable_appointment_confirmation_without_payment:
		return False
	if frappe.session.user == "Guest" or is_website_user():
		return False

	return bool(
		frappe.db.exists(
			"Service Appointment",
			{
				"booking_id": booking_id,
				"docstatus": 0,
				"status": ["not in", ["Cancelled", "Closed"]],
			},
		)
	)


def _get_checkout_appointments(booking_id: str):
	appointment_names = frappe.get_all(
		"Service Appointment",
		filters={"booking_id": booking_id, "docstatus": 0},
		pluck="name",
	)
	return [frappe.get_doc("Service Appointment", name) for name in appointment_names]


def _coupon_scope_label(coupon):
	return coupon_scope_label(coupon)


def _evaluate_coupon_for_booking(booking_id: str, coupon):
	booking = frappe.get_doc("Service Booking", booking_id)
	if is_booking_level_coupon(coupon):
		pricing = calculate_booking_pricing(booking, booking_coupon_code=coupon.name)
		booking_discount = flt(pricing.get("bookingDiscountAmount") or 0)
		valid = booking_discount > 0
		message = pricing.get("bookingCouponMessage") or _("Coupon is not applicable to this booking.")
		return {
			"eligible": (
				[] if not valid else [{"bookingId": booking_id, "discountAmount": booking_discount}]
			),
			"ineligible": ([] if valid else [{"bookingId": booking_id, "reason": message}]),
			"previewDiscount": booking_discount,
			"scope": _coupon_scope_label(coupon),
			"pricing": pricing,
		}

	appointments = _get_checkout_appointments(booking_id)
	eligible = []
	ineligible = []
	preview_discount = 0

	usage_ok, usage_msg = coupon.is_usage_available()

	for appointment in appointments:
		valid, reason = coupon.is_valid_for_appointment(appointment=appointment)
		if valid and usage_ok:
			discount = flt(appointment.compute_coupon_discount(coupon))
			eligible.append(
				{
					"appointmentId": appointment.name,
					"serviceType": appointment.appointment_type,
					"guestName": appointment.full_name,
					"totalAmount": flt(appointment.total_amount),
					"discountAmount": discount,
				}
			)
			preview_discount += discount
		else:
			ineligible.append(
				{
					"appointmentId": appointment.name,
					"serviceType": appointment.appointment_type,
					"guestName": appointment.full_name,
					"reason": usage_msg if not usage_ok else reason,
				}
			)

	return {
		"eligible": eligible,
		"ineligible": ineligible,
		"previewDiscount": preview_discount,
		"scope": _coupon_scope_label(coupon),
		"pricing": calculate_booking_pricing(booking),
	}


def _build_booking_coupon_summary(booking, pricing=None):
	pricing = pricing or calculate_booking_pricing(booking)
	applied_coupons = list(pricing.get("appointmentCoupons") or [])
	booking_coupon = pricing.get("bookingCoupon")
	if booking_coupon:
		applied_coupons.append(
			{
				"coupon": booking_coupon.get("code") or booking_coupon.get("name"),
				"discountAmount": flt(booking_coupon.get("discountAmount") or 0),
				"scope": "booking",
				"appointments": [],
			}
		)

	return {
		"hasCoupon": bool(applied_coupons),
		"totalDiscount": flt(pricing.get("appointmentDiscountTotal") or 0)
		+ flt(pricing.get("bookingDiscountAmount") or 0),
		"appointmentDiscountTotal": flt(pricing.get("appointmentDiscountTotal") or 0),
		"bookingDiscountAmount": flt(pricing.get("bookingDiscountAmount") or 0),
		"appliedCoupons": applied_coupons,
		"appliedBookingCoupon": booking_coupon,
		"appliedAppointmentCoupons": pricing.get("appointmentCoupons") or [],
	}


@frappe.whitelist()
def validate_checkout_coupon(booking_id: str, coupon_code: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	if not coupon_code:
		frappe.throw(_("Coupon code is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	coupon = resolve_coupon_doc(coupon_code)
	if not coupon:
		return {
			"valid": False,
			"message": _("That coupon code isn't valid. Check the code and try again."),
			"coupon": None,
			"evaluation": {
				"eligible": [],
				"ineligible": [],
				"previewDiscount": 0,
				"scope": "none",
			},
		}

	evaluation = _evaluate_coupon_for_booking(booking_id, coupon)
	valid = len(evaluation.get("eligible") or []) > 0
	ineligible = evaluation.get("ineligible") or []
	invalid_message = (
		ineligible[0].get("reason")
		if ineligible and isinstance(ineligible[0], dict)
		else _("Coupon is not applicable to this booking.")
	)

	return {
		"valid": valid,
		"message": (_("Coupon is valid.") if valid else invalid_message),
		"coupon": {
			"name": coupon.name,
			"code": coupon.code,
			"couponType": coupon.coupon_type,
			"discountType": coupon.discount_type,
			"discountValue": flt(coupon.discount_value),
			"maximumDiscountAmount": flt(coupon.maximum_discount_amount or 0),
			"minimumOrderValue": flt(coupon.minimum_order_value or 0),
			"scope": evaluation.get("scope"),
		},
		"evaluation": evaluation,
		"pricing": evaluation.get("pricing") or calculate_booking_pricing(booking),
	}


@frappe.whitelist()
def apply_checkout_coupon(booking_id: str, coupon_code: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	if not coupon_code:
		frappe.throw(_("Coupon code is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	coupon = resolve_coupon_doc(coupon_code)
	if not coupon:
		frappe.throw(_("That coupon code isn't valid. Check the code and try again."))

	# Non-stacking: reject booking coupon if any appointment coupon exists
	if is_booking_level_coupon(coupon):
		_assert_no_appointment_coupons(booking_id)
	else:
		frappe.throw(
			_(
				"Appointment-level coupons must be applied per appointment. "
				"Use the coupon field on each appointment card."
			)
		)

	evaluation = _evaluate_coupon_for_booking(booking_id, coupon)
	if not (evaluation.get("eligible") or []):
		ineligible = evaluation.get("ineligible") or []
		message = (
			ineligible[0].get("reason")
			if ineligible and isinstance(ineligible[0], dict)
			else _("Coupon is not applicable to this booking.")
		)
		frappe.throw(message)

	booking.coupon_code = coupon.name
	booking.save(ignore_permissions=True)

	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()
	frappe.db.commit()  # nosemgrep

	return {
		"message": _("Coupon applied successfully."),
		"checkout": _build_checkout_summary(booking),
		"evaluation": evaluation,
	}


@frappe.whitelist()
def remove_checkout_coupon(booking_id: str, coupon_code: str | None = None):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	filters = {"booking_id": booking_id, "docstatus": 0}
	remove_booking_coupon = False
	if coupon_code:
		coupon = resolve_coupon_doc(coupon_code)
		if coupon:
			if is_booking_level_coupon(coupon):
				remove_booking_coupon = True
			else:
				filters["coupon_code"] = coupon.name
		else:
			filters["coupon_code"] = coupon_code
	else:
		filters["coupon_code"] = ["is", "set"]
		remove_booking_coupon = True

	if remove_booking_coupon:
		booking.coupon_code = None
		booking.coupon_discount_type = ""
		booking.coupon_discount_amount = 0
		booking.coupon_scope = ""
		booking.save(ignore_permissions=True)

	appointment_names = frappe.get_all("Service Appointment", filters=filters, pluck="name")
	for appointment_name in appointment_names:
		appointment = frappe.get_doc("Service Appointment", appointment_name)
		appointment.coupon_code = None
		appointment.discount_amount = 0
		appointment.calculate_grand_total()
		appointment.set_confirmation_targets()
		appointment.set_outstanding_amount()
		appointment.update_payment_and_workflow_status()
		appointment.save(ignore_permissions=True)

	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()
	frappe.db.commit()  # nosemgrep

	return {
		"message": _("Coupon removed."),
		"checkout": _build_checkout_summary(booking),
	}


def _assert_no_appointment_coupons(booking_id: str):
	"""Raise if any appointment in the booking already has a coupon applied."""
	has_appt_coupon = frappe.db.exists(
		"Service Appointment",
		{"booking_id": booking_id, "docstatus": 0, "coupon_code": ["is", "set"]},
	)
	if has_appt_coupon:
		frappe.throw(
			_(
				"Appointment-level discounts are already active. "
				"Remove appointment coupons before applying a booking-level coupon."
			)
		)


def _assert_no_booking_coupon(booking):
	"""Raise if the booking already has a booking-level coupon."""
	if booking.coupon_code:
		frappe.throw(
			_("A booking-level coupon is already active. " "Remove it before applying an appointment coupon.")
		)


@frappe.whitelist()
def apply_appointment_coupon(booking_id: str, appointment_id: str, coupon_code: str):
	"""Apply a coupon to a single appointment only. Enforces non-stacking."""
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	if not appointment_id:
		frappe.throw(_("Appointment reference is required."))
	if not coupon_code:
		frappe.throw(_("Coupon code is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	appointment = frappe.get_doc("Service Appointment", appointment_id)

	if appointment.booking_id != booking_id:
		frappe.throw(_("Appointment does not belong to this booking."))

	coupon = resolve_coupon_doc(coupon_code)
	if not coupon:
		frappe.throw(_("That coupon code isn't valid. Check the code and try again."))

	if is_booking_level_coupon(coupon):
		frappe.throw(
			_(
				"This coupon applies to the entire booking, not a single appointment. "
				"Use the booking coupon field instead."
			)
		)

	# Non-stacking: reject if booking coupon is active.
	_assert_no_booking_coupon(booking)

	# Validate against this specific appointment.
	valid, reason = coupon.is_valid_for_appointment(appointment=appointment)
	if not valid:
		frappe.throw(reason or _("Coupon is not valid for this appointment."))

	usage_ok, usage_msg = coupon.is_usage_available()
	if not usage_ok:
		frappe.throw(usage_msg or _("Coupon usage limit has been reached."))

	appointment.coupon_code = coupon.name
	appointment.save(ignore_permissions=True)

	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()
	frappe.db.commit()  # nosemgrep

	return {
		"message": _("Coupon applied to appointment."),
		"checkout": _build_checkout_summary(booking),
	}


@frappe.whitelist()
def remove_appointment_coupon(booking_id: str, appointment_id: str):
	"""Remove the coupon from a single appointment."""
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	if not appointment_id:
		frappe.throw(_("Appointment reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	appointment = frappe.get_doc("Service Appointment", appointment_id)

	if appointment.booking_id != booking_id:
		frappe.throw(_("Appointment does not belong to this booking."))

	appointment.coupon_code = None
	appointment.discount_amount = 0
	appointment.calculate_grand_total()
	appointment.set_confirmation_targets()
	appointment.set_outstanding_amount()
	appointment.update_payment_and_workflow_status()
	appointment.save(ignore_permissions=True)

	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()
	frappe.db.commit()  # nosemgrep

	return {
		"message": _("Coupon removed from appointment."),
		"checkout": _build_checkout_summary(booking),
	}


def _get_booking_service_types(booking):
	service_types = []
	for item in booking.items:
		service_type = item.service_type
		if service_type and service_type not in service_types:
			service_types.append(service_type)
	return service_types


def _get_mode_of_payment_options():
	try:
		rows = frappe.get_all(
			"Mode of Payment",
			filters={"enabled": 1},
			fields=["name", "type"],
			order_by="name asc",
		)
	except Exception:
		rows = frappe.get_all("Mode of Payment", fields=["name"], order_by="name asc")

	options = []
	for row in rows:
		name = row.get("name") if isinstance(row, dict) else None
		if not name:
			continue
		label = name
		provider_type = "cash" if name.lower() == "cash" else "manual"
		options.append(
			{
				"id": f"mode:{name}",
				"label": label,
				"sourceType": "mode_of_payment",
				"providerType": provider_type,
				"modeOfPayment": name,
			}
		)
	return options


def _get_gateway_options(booking):
	service_types = _get_booking_service_types(booking)

	gateway_names = []
	for service_type in service_types:
		for gateway in get_payment_gateways_for_service_type(service_type):
			if gateway and gateway not in gateway_names:
				gateway_names.append(gateway)

	if not gateway_names:
		for gateway in get_payment_gateways_for_service_type(None):
			if gateway and gateway not in gateway_names:
				gateway_names.append(gateway)

	options = []
	for gateway in gateway_names:
		provider_type = "mpesa" if "mpesa" in gateway.lower() else "hosted"
		capabilities = ["redirect", "link"]
		if provider_type == "mpesa":
			capabilities = ["mpesa", "link"]

		options.append(
			{
				"id": f"gateway:{gateway}",
				"label": gateway,
				"sourceType": "gateway",
				"providerType": provider_type,
				"gateway": gateway,
				"capabilities": capabilities,
			}
		)

	return options


@frappe.whitelist()
def get_checkout_summary(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()

	return _build_checkout_summary(booking)


@frappe.whitelist()
def confirm_checkout_without_payment(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	if not _can_confirm_checkout_without_payment(booking.name):
		frappe.throw(
			_("Booking cannot be confirmed without payment."),
			title=_("Payment Required"),
		)

	appointments = _get_checkout_appointments(booking.name)
	if not appointments:
		frappe.throw(_("No draft appointments found for this booking."), title=_("Invalid State"))

	confirmed = []
	processed = set()
	for appointment in appointments:
		if appointment.name in processed:
			continue
		if appointment.couple_appointment_id and not appointment.is_primary_in_couple:
			appointment = frappe.get_doc("Service Appointment", appointment.couple_appointment_id)
			if appointment.name in processed:
				continue
		if appointment.status in ["Cancelled", "Closed"]:
			continue
		appointment.confirm_appointment()
		confirmed.append(appointment.name)
		processed.add(appointment.name)
		if appointment.couple_appointment_id:
			confirmed.append(appointment.couple_appointment_id)
			processed.add(appointment.couple_appointment_id)

	booking.reload()
	booking.sync_financial_snapshot()
	frappe.db.commit()  # nosemgrep - checkout confirmation is an explicit desk action boundary.

	return {
		"confirmedAppointments": confirmed,
		"checkout": _build_checkout_summary(booking),
	}


@frappe.whitelist()
def get_checkout_payment_methods(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	methods = _get_gateway_options(booking)
	methods.extend(_get_mode_of_payment_options())

	default_method_id = ""
	if methods:
		mpesa = next(
			(method for method in methods if method.get("providerType") == "mpesa"),
			None,
		)
		default_method_id = (mpesa or methods[0]).get("id")

	return {
		"methods": methods,
		"defaultMethodId": default_method_id,
	}


@frappe.whitelist()
def get_checkout_offline_payment_methods(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	# Validate booking context even though offline methods are global configuration.
	frappe.get_doc("Service Booking", booking_id)
	methods = _get_mode_of_payment_options()
	default_method_id = methods[0].get("id") if methods else ""
	return {
		"methods": methods,
		"defaultMethodId": default_method_id,
	}


@frappe.whitelist()
def get_checkout_online_payment_gateways(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	methods = _get_gateway_options(booking)
	default_method_id = ""
	if methods:
		mpesa = next(
			(method for method in methods if method.get("providerType") == "mpesa"),
			None,
		)
		default_method_id = (mpesa or methods[0]).get("id")

	return {
		"methods": methods,
		"defaultMethodId": default_method_id,
	}


@frappe.whitelist()
def create_checkout_payment_link(
	booking_id: str,
	payment_gateway: str | None = None,
	redirect_to: str | None = None,
	phone_number: str | None = None,
	amount: float | None = None,
	payment_type: str | None = None,
	coupon_code: str | None = None,
	final_amount_reference: float | None = None,
):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	if phone_number:
		frappe.db.set_value("Service Booking", booking_id, "mobile_no", phone_number)

	frappe.logger("frappoint.checkout").info(
		{
			"event": "create_checkout_payment_link",
			"booking_id": booking_id,
			"payment_gateway": payment_gateway,
			"payment_type": payment_type,
			"coupon_code": coupon_code,
			"amount": amount,
			"final_amount_reference": final_amount_reference,
		}
	)

	url = get_payment_link(
		reference_doctype="Service Booking",
		reference_docname=booking_id,
		payment_gateway=payment_gateway or "",
		redirect_to=redirect_to or "",
		amount=amount,
		payment_type=payment_type,
		coupon_code=coupon_code,
	)

	booking = frappe.get_doc("Service Booking", booking_id)
	booking.reload()

	return {
		"url": url,
		"checkout": _build_checkout_summary(booking),
	}


@frappe.whitelist()
def record_manual_checkout_payment(
	booking_id: str,
	amount: float,
	mode_of_payment: str | None = None,
	reference_no: str | None = None,
):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))

	booking = frappe.get_doc("Service Booking", booking_id)
	pay_amount = flt(amount)

	if pay_amount <= 0:
		frappe.throw(_("Payment amount must be greater than zero."))

	if pay_amount > flt(booking.outstanding_amount):
		frappe.throw(_("Payment amount cannot exceed outstanding balance."))

	payment_doc = frappe.new_doc("Service Appointment Payment")
	payment_doc.user = frappe.session.user
	payment_doc.amount = pay_amount
	payment_doc.currency = booking.currency
	payment_doc.reference_doctype = "Service Booking"
	payment_doc.reference_docname = booking.name
	payment_doc.payment_received = 1

	if mode_of_payment:
		payment_doc.mode_of_payment = mode_of_payment

	if reference_no:
		payment_doc.payment_id = reference_no
		payment_doc.order_id = reference_no

	payment_doc.insert(ignore_permissions=True)
	payment_doc.submit()

	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()

	frappe.db.commit()  # nosemgrep

	return {
		"paymentName": payment_doc.name,
		"checkout": _build_checkout_summary(booking),
	}


def _is_truthy(value) -> bool:
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "on"}
	return bool(value)


def _payload_value(payload, *keys, default=None):
	if not isinstance(payload, dict):
		return default
	for key in keys:
		if key in payload and payload.get(key) is not None:
			return payload.get(key)
	return default


def _provider_reference(value):
	if isinstance(value, dict):
		return _payload_value(value, "provider", "providerId", "provider_id", "name", "id")
	return value


def _lock_service_booking_row(booking_name: str) -> None:
	frappe.db.sql(
		"""
		SELECT name
		FROM `tabService Booking`
		WHERE name = %(booking_name)s
		FOR UPDATE
		""",
		{"booking_name": booking_name},
	)


def _lock_service_appointment_rows(appointment_names: list[str]) -> None:
	names = sorted({str(name) for name in appointment_names if name})
	if not names:
		return
	frappe.db.sql(
		"""
		SELECT name
		FROM `tabService Appointment`
		WHERE name IN %(appointment_names)s
		ORDER BY name
		FOR UPDATE
		""",
		{"appointment_names": tuple(names)},
	)


def _queue_couple_calendar_sync(appointments, event_status: str | None = None) -> None:
	for appointment in appointments:
		frappe.enqueue(
			"frappoint.frappoint.doctype.service_appointment.service_appointment.sync_calendar_event_after_commit",
			appointment_name=appointment.name,
			event_status=event_status,
			enqueue_after_commit=True,
		)


def _normalise_couple_guest(value, booking, guest_number: int) -> dict:
	guest = _parse_json_payload(value, {}) or {}
	if not isinstance(guest, dict):
		frappe.throw(_("Guest {0} details must be an object.").format(guest_number))

	full_name = _payload_value(guest, "fullName", "full_name", "guestFullName", "guest_full_name")
	if guest_number == 1:
		full_name = full_name or booking.full_name
	if not full_name:
		frappe.throw(_("Guest {0} full name is required for a couple booking.").format(guest_number))

	return {
		"full_name": full_name,
		"email": _payload_value(guest, "email", "guestEmail", "guest_email") or booking.email,
		"mobile_no": _payload_value(guest, "mobileNo", "mobile_no", "guestMobileNo", "guest_mobile_no")
		or booking.mobile_no,
		"notes": _payload_value(guest, "notes", default=""),
		"provider_gender": _payload_value(guest, "providerGender", "provider_gender"),
	}


def _normalise_service_payload(service_value, assignment: dict, index: int) -> dict:
	if isinstance(service_value, str):
		service_payload = {"serviceType": service_value}
	elif isinstance(service_value, dict):
		service_payload = dict(service_value)
	else:
		service_payload = {}

	nested = _payload_value(assignment, f"service_{index}", f"service{index}", default={}) or {}
	if isinstance(nested, str):
		nested = {"serviceType": nested}
	if isinstance(nested, dict):
		service_payload = {**service_payload, **nested}

	service_type = _payload_value(service_payload, "serviceType", "service_type", "serviceId", "service_id")
	direct_service_type = _payload_value(assignment, f"service_type_{index}", f"serviceType{index}")
	if isinstance(direct_service_type, str):
		service_type = direct_service_type
	if not service_type:
		frappe.throw(_("Service type is required for guest {0}.").format(index))
	service_payload["serviceType"] = service_type
	if not _payload_value(service_payload, "duration"):
		service_payload["duration"] = _payload_value(assignment, f"duration_{index}", f"duration{index}")
	return service_payload


def _normalise_couple_slot(assignment: dict) -> tuple[dict, dict, dict]:
	slot = _payload_value(assignment, "selected_time_slot", "selectedTimeSlot", "slot", default={})
	slot = _parse_json_payload(slot, {}) or {}
	if not isinstance(slot, dict):
		frappe.throw(_("Selected couple time slot must be an object."))

	leg_1 = _payload_value(slot, "guest_1", "guest1", "service_1", "service1", default={}) or {}
	leg_2 = _payload_value(slot, "guest_2", "guest2", "service_2", "service2", default={}) or {}
	if not isinstance(leg_1, dict):
		leg_1 = {}
	if not isinstance(leg_2, dict):
		leg_2 = {}

	# Some clients return alternative provider pairs. Resolve the requested pair, or the first pair.
	pair_options = _payload_value(slot, "provider_pairs", "providerPairs", "providers", default=[]) or []
	preferred_1 = _provider_reference(
		_payload_value(assignment, "preferred_provider_1", "preferredProvider1")
	)
	preferred_2 = _provider_reference(
		_payload_value(assignment, "preferred_provider_2", "preferredProvider2")
	)
	if isinstance(pair_options, list):
		for option in pair_options:
			if not isinstance(option, dict):
				continue
			option_1 = _payload_value(option, "guest_1", "guest1", default={}) or {}
			option_2 = _payload_value(option, "guest_2", "guest2", default={}) or {}
			provider_1 = _provider_reference(
				_payload_value(option_1, "provider", "provider_id", "providerId")
				or _payload_value(option, "provider_1", "provider1")
			)
			provider_2 = _provider_reference(
				_payload_value(option_2, "provider", "provider_id", "providerId")
				or _payload_value(option, "provider_2", "provider2")
			)
			if preferred_1 and provider_1 != preferred_1:
				continue
			if preferred_2 and provider_2 != preferred_2:
				continue
			leg_1 = {**leg_1, **option_1, "provider": provider_1}
			leg_2 = {**leg_2, **option_2, "provider": provider_2}
			break

	return slot, leg_1, leg_2


def _resolve_couple_member(
	booking,
	assignment: dict,
	guest: dict,
	service_payload: dict,
	slot: dict,
	leg: dict,
	index: int,
) -> dict:
	service_type = service_payload["serviceType"]
	price_id = _payload_value(service_payload, "priceId", "price_id", "packageId", "package_id")
	amount = _payload_value(service_payload, "price", "rate", "amount")
	requested_duration = cint(
		_payload_value(service_payload, "duration", default=_payload_value(leg, "duration")) or 0
	)
	price_doc = _get_price_doc(
		service_type,
		price_id=price_id,
		amount=amount,
		duration=requested_duration or None,
		pricing_model=_payload_value(service_payload, "pricingModel", "pricing_model"),
	)
	service_config = (
		frappe.db.get_value(
			"Service Type",
			service_type,
			["default_duration_in_minutes", "buffer_before", "buffer_after"],
			as_dict=True,
		)
		or {}
	)
	price_duration = cint(price_doc.duration if price_doc else 0)
	if price_duration > 0 and requested_duration > 0 and price_duration != requested_duration:
		frappe.throw(
			_("The selected duration for guest {0} does not match the selected service price.").format(index)
		)
	duration = (
		price_duration or requested_duration or cint(service_config.get("default_duration_in_minutes") or 0)
	)
	if duration <= 0:
		frappe.throw(_("A positive duration is required for guest {0}'s service.").format(index))

	appointment_date = _payload_value(
		slot, "date", "appointment_date", "appointmentDate", "start_date", "startDate"
	) or _payload_value(assignment, "date", "appointment_date", "appointmentDate")
	start_time = _payload_value(slot, "start_time", "startTime") or _payload_value(
		leg, "start_time", "startTime"
	)
	leg_start_time = _payload_value(leg, "start_time", "startTime")
	if leg_start_time and start_time and get_time(leg_start_time) != get_time(start_time):
		frappe.throw(_("Both couple services must start at the same time."))
	end_time = _payload_value(leg, "end_time", "endTime")
	if not appointment_date or not start_time:
		frappe.throw(_("The selected couple slot must include a date and shared start time."))
	expected_end = get_datetime(f"{appointment_date} {start_time}") + timedelta(minutes=duration)
	if not end_time:
		end_time = expected_end.time()
	elif get_time(end_time) != expected_end.time():
		frappe.throw(
			_("Guest {0}'s slot end time does not match the selected service duration.").format(index)
		)

	preferred_provider = _provider_reference(
		_payload_value(assignment, f"preferred_provider_{index}", f"preferredProvider{index}")
	)
	selected_provider = _provider_reference(
		_payload_value(leg, "provider", "provider_id", "providerId")
	) or _provider_reference(_payload_value(slot, f"provider_{index}", f"provider{index}"))
	if preferred_provider and selected_provider and preferred_provider != selected_provider:
		frappe.throw(
			_("Guest {0}'s preferred provider does not match the selected couple slot.").format(index)
		)
	provider = preferred_provider or selected_provider
	if not provider:
		frappe.throw(_("An available provider is required for guest {0}.").format(index))

	service_unit = _payload_value(leg, "service_unit", "serviceUnit") or _payload_value(
		slot, f"service_unit_{index}", f"serviceUnit{index}"
	)
	if price_doc and amount is not None and flt(amount) != flt(price_doc.amount):
		frappe.throw(_("Guest {0}'s service amount does not match the selected price.").format(index))
	amount = price_doc.amount if price_doc else (amount or 0)
	requested_currency = _payload_value(service_payload, "currency")
	if price_doc and requested_currency and requested_currency != price_doc.currency:
		frappe.throw(_("Guest {0}'s service currency does not match the selected price.").format(index))
	currency = price_doc.currency if price_doc else (requested_currency or booking.currency)
	resolved_price_name = price_id or (price_doc.price_name if price_doc else None)
	if not resolved_price_name:
		frappe.throw(_("A service price is required for guest {0}.").format(index))

	return {
		"guest": guest,
		"service_type": service_type,
		"appointment_date": appointment_date,
		"start_time": start_time,
		"end_time": end_time,
		"provider": provider,
		"service_unit": service_unit,
		"duration": duration,
		"appointment_price": resolved_price_name,
		"currency": currency,
		"amount": amount,
		"buffer_before": cint(service_config.get("buffer_before") or 0),
		"buffer_after": cint(service_config.get("buffer_after") or 0),
		"slot_ids": _payload_value(leg, "slot_ids", "slotIds", default=[]) or [],
		"provider_options": _payload_value(leg, "providers", default=[]) or [],
	}


def _apply_couple_member_to_appointment(appointment, booking, member: dict) -> None:
	guest = member["guest"]
	appointment.booking_id = booking.name
	appointment.source = appointment.source or "Booking Desk"
	appointment.status = appointment.status or "Open"
	appointment.customer = booking.customer
	appointment.appointment_type = member["service_type"]
	appointment.appointment_date = member["appointment_date"]
	appointment.appointment_provider = member["provider"]
	appointment.service_unit = member["service_unit"]
	appointment.duration = member["duration"]
	appointment.appointment_price = member["appointment_price"]
	appointment.currency = member["currency"]
	appointment.start_time = member["start_time"]
	appointment.end_time = member["end_time"]
	appointment.buffer_before_minutes = member["buffer_before"]
	appointment.buffer_after_minutes = member["buffer_after"]
	appointment.selected_slot_ids = json.dumps(member["slot_ids"]) if member["slot_ids"] else None
	appointment.all_available_providers = json.dumps(member["provider_options"])
	appointment.full_name = guest["full_name"]
	appointment.email = guest["email"]
	appointment.mobile_no = guest["mobile_no"]
	appointment.total_amount = member["amount"]
	appointment.notes = guest["notes"]
	appointment.set("guests", [])
	appointment.append(
		"guests",
		{
			"full_name": guest["full_name"],
			"email": guest["email"],
			"mobile_no": guest["mobile_no"],
			"is_primary": 1,
			"notes": guest["notes"],
		},
	)


def _validate_couple_members_against_projector(member_1: dict, member_2: dict) -> None:
	"""Re-resolve the selected provider/unit pair from authoritative counter availability."""
	appointment_date = getdate(member_1["appointment_date"])
	rows = get_projected_couple_available_slots(
		service_type_1=member_1["service_type"],
		service_type_2=member_2["service_type"],
		start_date=appointment_date,
		end_date=appointment_date,
		provider_1=member_1["provider"],
		provider_2=member_2["provider"],
		service_unit_1=member_1["service_unit"],
		service_unit_2=member_2["service_unit"],
		duration_1=member_1["duration"],
		duration_2=member_2["duration"],
	)
	for row in rows:
		guest_1 = row.get("guest_1") or {}
		guest_2 = row.get("guest_2") or {}
		if (
			getdate(row.get("date")) == appointment_date
			and get_time(row.get("start_time")) == get_time(member_1["start_time"])
			and get_time(guest_1.get("end_time")) == get_time(member_1["end_time"])
			and get_time(guest_2.get("end_time")) == get_time(member_2["end_time"])
			and guest_1.get("provider") == member_1["provider"]
			and guest_2.get("provider") == member_2["provider"]
			and (guest_1.get("service_unit") or None) == (member_1["service_unit"] or None)
			and (guest_2.get("service_unit") or None) == (member_2["service_unit"] or None)
		):
			return

	frappe.throw(
		_("The selected provider/unit pair is no longer available for both couple services."),
		title=_("Couple Slot Unavailable"),
	)


def _appointment_as_couple_member(appointment) -> dict:
	return {
		"service_type": appointment.appointment_type,
		"appointment_date": appointment.appointment_date,
		"start_time": appointment.start_time,
		"end_time": appointment.end_time,
		"provider": appointment.appointment_provider,
		"service_unit": appointment.service_unit,
		"duration": cint(appointment.duration),
	}


def _validate_couple_booking_items(booking, members: list[dict]) -> None:
	"""Ensure the operational pair is covered by the booking lines later used for billing."""
	available = []
	for item in booking.items or []:
		for _index in range(max(0, cint(item.qty) - cint(item.cancelled_qty or 0))):
			available.append(
				{
					"service_type": item.service_type,
					"rate": flt(item.rate),
					"currency": item.currency or booking.currency,
				}
			)

	for member_index, member in enumerate(members, start=1):
		match_index = next(
			(
				index
				for index, item in enumerate(available)
				if item["service_type"] == member["service_type"]
				and abs(item["rate"] - flt(member["amount"])) < 0.000001
				and item["currency"] == member["currency"]
			),
			None,
		)
		if match_index is None:
			frappe.throw(
				_("The booking items do not contain guest {0}'s selected service and price.").format(
					member_index
				),
				title=_("Couple Service Mismatch"),
			)
		available.pop(match_index)


def _couple_reservation_request(appointment) -> dict:
	allocation_status = (
		"Confirmed"
		if appointment.status in ["Confirmed", "Checked In", "In Progress", "Completed"]
		else "Held"
	)
	return {
		"appointment_name": appointment.name,
		"booking_name": appointment.booking_id,
		"allocations": appointment._build_allocation_payloads(),
		"allocation_status": allocation_status,
		"extra_metadata": {
			"source": "booking_desk.couple_booking",
			"couple_appointment_id": appointment.couple_appointment_id,
		},
	}


def _upsert_couple_appointments(booking, assignment: dict) -> list:
	from frappoint.frappoint.services.booking_transaction_service import (
		release_couple_appointment_allocations,
		reserve_couple_appointment_allocations,
	)

	guest_1 = _normalise_couple_guest(_payload_value(assignment, "guest_1", "guest1"), booking, 1)
	guest_2 = _normalise_couple_guest(_payload_value(assignment, "guest_2", "guest2"), booking, 2)
	service_1 = _normalise_service_payload(
		_payload_value(assignment, "service_type_1", "serviceType1"), assignment, 1
	)
	service_2 = _normalise_service_payload(
		_payload_value(assignment, "service_type_2", "serviceType2"), assignment, 2
	)
	slot, leg_1, leg_2 = _normalise_couple_slot(assignment)
	member_1 = _resolve_couple_member(booking, assignment, guest_1, service_1, slot, leg_1, 1)
	member_2 = _resolve_couple_member(booking, assignment, guest_2, service_2, slot, leg_2, 2)

	if str(member_1["appointment_date"]) != str(member_2["appointment_date"]):
		frappe.throw(_("Both couple appointments must use the same appointment date."))
	if get_time(member_1["start_time"]) != get_time(member_2["start_time"]):
		frappe.throw(_("Both couple appointments must start at the same time."))
	appointment_id_1 = _payload_value(
		assignment, "appointment_id_1", "appointmentId1", "primary_appointment_id"
	)
	appointment_id_2 = _payload_value(
		assignment, "appointment_id_2", "appointmentId2", "secondary_appointment_id"
	)
	if bool(appointment_id_1) != bool(appointment_id_2):
		frappe.throw(_("Both appointment references are required when updating a couple booking."))

	savepoint = f"couple_booking_{now_datetime().strftime('%H%M%S%f')}"
	frappe.db.savepoint(savepoint)
	try:
		_lock_service_booking_row(booking.name)
		booking.reload()
		if booking.docstatus != 0 or booking.status in {"Cancelled", "Closed"}:
			frappe.throw(_("Only an active draft booking can accept couple appointments."))
		if not cint(getattr(booking, "is_couple", 0)):
			booking.db_set("is_couple", 1, update_modified=False)
			booking.is_couple = 1
		_validate_couple_booking_items(booking, [member_1, member_2])
		if appointment_id_1:
			_lock_service_appointment_rows([appointment_id_1, appointment_id_2])
			appointments = [
				frappe.get_doc("Service Appointment", appointment_id_1),
				frappe.get_doc("Service Appointment", appointment_id_2),
			]
			if any(appointment.booking_id != booking.name for appointment in appointments):
				frappe.throw(_("Both couple appointments must belong to booking {0}.").format(booking.name))
			if appointments[0].couple_appointment_id != appointments[1].name or (
				appointments[1].couple_appointment_id != appointments[0].name
			):
				frappe.throw(_("The supplied appointments are not a linked couple."))
			release_couple_appointment_allocations(
				appointment_names=[appointment.name for appointment in appointments],
				target_status="Released",
			)
		else:
			existing_couple = frappe.get_all(
				"Service Appointment",
				filters={
					"booking_id": booking.name,
					"couple_appointment_id": ["is", "set"],
					"docstatus": ["!=", 2],
				},
				pluck="name",
				limit=1,
			)
			if existing_couple:
				frappe.throw(
					_(
						"This booking already has couple appointments. "
						"Pass both appointment IDs to update them."
					)
				)
			appointments = [frappe.new_doc("Service Appointment"), frappe.new_doc("Service Appointment")]

		# Updates release their own held rows above, so this exact projection check
		# evaluates provider/unit correlation against the same counters we reserve.
		_validate_couple_members_against_projector(member_1, member_2)

		for appointment, member in zip(appointments, [member_1, member_2], strict=True):
			appointment.flags.skip_resource_allocation = True
			appointment.flags.skip_calendar_event = True
			appointment.flags.skip_couple_validation = True
			appointment.flags.skip_capacity_validation = True
			appointment.flags.skip_couple_auto_confirmation = True
			appointment.flags.allow_couple_update = True
			_apply_couple_member_to_appointment(appointment, booking, member)
			if appointment.is_new():
				appointment.insert(ignore_permissions=True)
			else:
				appointment.save(ignore_permissions=True)

		primary, secondary = appointments
		frappe.db.set_value(
			"Service Appointment",
			primary.name,
			{"couple_appointment_id": secondary.name, "is_primary_in_couple": 1},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Appointment",
			secondary.name,
			{"couple_appointment_id": primary.name, "is_primary_in_couple": 0},
			update_modified=False,
		)
		primary.couple_appointment_id = secondary.name
		primary.is_primary_in_couple = 1
		secondary.couple_appointment_id = primary.name
		secondary.is_primary_in_couple = 0

		for appointment in appointments:
			appointment.flags.skip_couple_validation = False
			appointment.validate_provider_offers_service()
			appointment.validate_couple_configuration()

		reserve_couple_appointment_allocations(
			appointments=[_couple_reservation_request(appointment) for appointment in appointments]
		)
		_queue_couple_calendar_sync(appointments)
		return appointments
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _couple_assignment_from_arguments(
	guest_1=None,
	guest_2=None,
	service_type_1=None,
	service_type_2=None,
	selected_time_slot=None,
	preferred_provider_1=None,
	preferred_provider_2=None,
	couple_assignment=None,
) -> dict:
	assignment = _parse_json_payload(couple_assignment, {}) or {}
	if not isinstance(assignment, dict):
		frappe.throw(_("Couple assignment must be an object."))
	values = {
		"guest_1": _parse_json_payload(guest_1, {}) if guest_1 is not None else None,
		"guest_2": _parse_json_payload(guest_2, {}) if guest_2 is not None else None,
		"service_type_1": _parse_json_payload(service_type_1, {})
		if isinstance(service_type_1, str) and service_type_1.strip().startswith("{")
		else service_type_1,
		"service_type_2": _parse_json_payload(service_type_2, {})
		if isinstance(service_type_2, str) and service_type_2.strip().startswith("{")
		else service_type_2,
		"selected_time_slot": _parse_json_payload(selected_time_slot, {})
		if selected_time_slot is not None
		else None,
		"preferred_provider_1": preferred_provider_1,
		"preferred_provider_2": preferred_provider_2,
	}
	for key, value in values.items():
		if value is not None:
			assignment[key] = value
	return assignment


@frappe.whitelist()
def create_draft_service_booking(
	customer: str | dict | None = None,
	items: str | list | None = None,
	booked_by: str | None = None,
	is_couple: int | str | bool = 0,
	guest_1: str | dict | None = None,
	guest_2: str | dict | None = None,
	service_type_1: str | dict | None = None,
	service_type_2: str | dict | None = None,
	selected_time_slot: str | dict | None = None,
	preferred_provider_1: str | dict | None = None,
	preferred_provider_2: str | dict | None = None,
	couple_assignment: str | dict | None = None,
	isCouple: int | str | bool | None = None,
):
	customer = _parse_json_payload(customer, {})
	items = _parse_json_payload(items, [])
	booked_by = (booked_by or "").strip()
	couple_mode = _is_truthy(isCouple if isCouple is not None else is_couple) or bool(couple_assignment)

	if not customer or not customer.get("customer"):
		frappe.throw(_("Customer is required before continuing the booking."))
	if not items:
		frappe.throw(_("Add at least one service before creating a draft booking."))
	if not booked_by:
		frappe.throw(_("Booked By is required before continuing the booking."))

	booking = frappe.new_doc("Service Booking")
	booking.customer = customer.get("customer")
	booking.full_name = customer.get("fullName") or customer.get("name")
	booking.email = customer.get("email")
	booking.mobile_no = customer.get("mobileNo")
	booking.booked_by = booked_by
	booking.booking_date = frappe.utils.today()
	booking.booking_time = frappe.utils.now_datetime()
	booking.status = "Draft"
	booking.is_couple = cint(couple_mode)
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

	assignment = _couple_assignment_from_arguments(
		guest_1=guest_1,
		guest_2=guest_2,
		service_type_1=service_type_1,
		service_type_2=service_type_2,
		selected_time_slot=selected_time_slot,
		preferred_provider_1=preferred_provider_1,
		preferred_provider_2=preferred_provider_2,
		couple_assignment=couple_assignment,
	)
	created_couple = []
	if couple_mode and _payload_value(assignment, "selected_time_slot", "selectedTimeSlot", "slot"):
		created_couple = _upsert_couple_appointments(booking, assignment)
		booking.reload()
		booking.sync_financial_snapshot()
		booking.reload()
	frappe.db.commit()  # nosemgrep - draft booking must be persisted before the desk continues.

	response = _serialize_booking(booking)
	if couple_mode:
		response["isCouple"] = True
		response["coupleAppointments"] = [
			_serialize_appointment(appointment) for appointment in created_couple
		]
	return response


@frappe.whitelist()
def upsert_draft_couple_appointments(
	booking_id: str | None = None,
	couple_assignment: str | dict | None = None,
	guest_1: str | dict | None = None,
	guest_2: str | dict | None = None,
	service_type_1: str | dict | None = None,
	service_type_2: str | dict | None = None,
	selected_time_slot: str | dict | None = None,
	preferred_provider_1: str | dict | None = None,
	preferred_provider_2: str | dict | None = None,
	bookingId: str | None = None,
):
	"""Create or update the two linked draft appointments as one atomic reservation."""
	booking_id = (
		booking_id or bookingId or frappe.form_dict.get("booking_id") or frappe.form_dict.get("bookingId")
	)
	if not booking_id:
		frappe.throw(_("Booking reference is required to reserve a couple appointment."))

	booking = frappe.get_doc("Service Booking", booking_id)
	if booking.docstatus != 0 or booking.status in {"Cancelled", "Closed"}:
		frappe.throw(_("Only an active draft booking can accept couple appointments."))

	assignment = _couple_assignment_from_arguments(
		guest_1=guest_1,
		guest_2=guest_2,
		service_type_1=service_type_1,
		service_type_2=service_type_2,
		selected_time_slot=selected_time_slot,
		preferred_provider_1=preferred_provider_1,
		preferred_provider_2=preferred_provider_2,
		couple_assignment=couple_assignment,
	)
	appointments = _upsert_couple_appointments(booking, assignment)
	booking.reload()
	booking.sync_financial_snapshot()
	booking.reload()
	frappe.db.commit()  # nosemgrep - both appointments and allocations share this transaction boundary.

	serialized = [_serialize_appointment(appointment) for appointment in appointments]
	return {
		"booking": _serialize_booking(booking),
		"appointments": serialized,
		"primaryAppointment": serialized[0],
		"secondaryAppointment": serialized[1],
	}


@frappe.whitelist()
def upsert_draft_service_appointment(
	booking_id: str | None = None,
	assignment: str | dict | None = None,
	appointment_id: str | None = None,
	bookingId: str | None = None,
):
	assignment = _parse_json_payload(assignment, {})
	booking_id = (
		booking_id or bookingId or frappe.form_dict.get("booking_id") or frappe.form_dict.get("bookingId")
	)
	if not booking_id:
		frappe.throw(_("Booking reference is required to reserve an appointment."))

	booking = frappe.get_doc("Service Booking", booking_id)
	service_type = assignment.get("serviceType") or assignment.get("serviceId")
	guest = assignment.get("guest") or {}
	slot = assignment.get("slot") or {}
	service_item = assignment.get("service") or {}
	service_payload = {**assignment, **service_item}
	slot_start_time = slot.get("startTime") or slot.get("start_time")
	slot_end_time = slot.get("endTime") or slot.get("end_time")
	slot_providers = slot.get("providers") or []
	provider = slot.get("provider") or slot.get("appointment_provider")
	service_unit = slot.get("serviceUnit") or slot.get("service_unit")
	if not provider and slot_providers:
		preferred_gender = guest.get("providerGender") or assignment.get("providerGender")
		selected_provider = select_provider_for_assignment(
			slot_providers,
			appointment_date=assignment.get("date"),
			service_type=service_type,
			preferred_gender=preferred_gender,
		)
		if not selected_provider:
			throw_no_provider_available(preferred_gender)
		provider = selected_provider.get("provider")
		service_unit = service_unit or selected_provider.get("service_unit")
	if not service_unit and slot_providers:
		matching_provider = next(
			(
				row
				for row in slot_providers
				if (row or {}).get("provider") == provider
				and ((row or {}).get("serviceUnit") or (row or {}).get("service_unit"))
			),
			None,
		)
		if matching_provider:
			service_unit = (matching_provider or {}).get("serviceUnit") or (matching_provider or {}).get(
				"service_unit"
			)
	slot_ids = slot.get("slotIds") or slot.get("slot_ids") or []

	if not service_type:
		frappe.throw(_("Service type is required to create an appointment."))
	if not guest.get("fullName"):
		frappe.throw(_("Guest full name is required before reserving a slot."))
	if not assignment.get("date"):
		frappe.throw(_("Appointment date is required before reserving a slot."))
	if not slot_start_time or not slot_end_time:
		frappe.throw(_("Selected slot is incomplete."))
	if not provider:
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
	appointment.appointment_provider = provider
	appointment.service_unit = service_unit
	appointment.duration = duration
	appointment.appointment_price = resolved_price_name
	appointment.currency = currency
	appointment.start_time = slot_start_time
	appointment.end_time = slot_end_time
	appointment.selected_slot_ids = json.dumps(slot_ids) if slot_ids else None
	appointment.all_available_providers = json.dumps(slot_providers)
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
	frappe.db.commit()  # nosemgrep - draft appointment must be persisted before returning availability state.

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
			"notes": appointment.notes,
			"slotIds": (json.loads(appointment.selected_slot_ids) if appointment.selected_slot_ids else []),
		},
	}


@frappe.whitelist()
def update_draft_service_appointment_notes(
	appointment_id: str | None = None,
	notes: str | None = None,
	appointmentId: str | None = None,
):
	appointment_id = (
		appointment_id
		or appointmentId
		or frappe.form_dict.get("appointment_id")
		or frappe.form_dict.get("appointmentId")
	)
	if not appointment_id:
		frappe.throw(_("Appointment reference is required to update notes."))

	appointment = frappe.get_doc("Service Appointment", appointment_id)
	appointment.notes = notes or ""
	for guest in appointment.get("guests") or []:
		if guest.get("is_primary"):
			guest.notes = appointment.notes
			break
	appointment.save(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep

	return {
		"name": appointment.name,
		"notes": appointment.notes,
	}


@frappe.whitelist()
def get_draft_service_booking(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	booking = frappe.get_doc("Service Booking", booking_id)
	return _serialize_booking(booking)


@frappe.whitelist()
def get_booking_details(booking_id: str):
	if not booking_id:
		frappe.throw(_("Booking reference is required."))
	booking = frappe.get_doc("Service Booking", booking_id)
	return _serialize_booking(booking)


@frappe.whitelist()
def get_appointment_details(appointment_id: str):
	if not appointment_id:
		frappe.throw(_("Appointment reference is required."))
	appointment = frappe.get_doc("Service Appointment", appointment_id)
	booking = frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
	return _build_appointment_response(appointment, booking)


def _cancel_service_appointment_without_commit(
	appointment,
	cancellation_reasons=None,
	capacity_already_released: bool = False,
	queue_calendar_sync: bool = True,
):
	if appointment.docstatus == 2 or appointment.status in {"Cancelled", "Closed"}:
		return {
			"success": True,
			"message": _("Appointment is already cancelled"),
			"appointment": appointment.name,
		}
	if appointment.docstatus == 1:
		return cancel_appointment(
			appointment.name,
			cancellation_reasons=cancellation_reasons,
			allow_couple_single=True,
			defer_calendar_sync=queue_calendar_sync,
			skip_calendar_status_sync=not queue_calendar_sync,
			skip_capacity_release=capacity_already_released,
			commit=False,
		)
	if appointment.docstatus != 0:
		frappe.throw(_("Appointment {0} cannot be cancelled in its current state.").format(appointment.name))

	reasons = _parse_json_payload(cancellation_reasons, []) or []
	if isinstance(reasons, str):
		reasons = [reasons]
	appointment.set("cancellation_reasons", [])
	for reason in reasons:
		appointment.append("cancellation_reasons", {"lost_reason": reason})
	appointment.flags.allow_couple_lifecycle = True
	appointment.flags.defer_calendar_sync = queue_calendar_sync
	appointment.flags.skip_calendar_status_sync = not queue_calendar_sync
	appointment.flags.skip_capacity_release = capacity_already_released
	appointment.status = "Cancelled"
	appointment.save(ignore_permissions=True)
	return {
		"success": True,
		"message": _("Appointment cancelled successfully"),
		"appointment": appointment.name,
	}


def _cancel_single_from_desk(appointment, cancellation_reasons=None):
	booking_name = appointment.booking_id
	savepoint = f"appointment_cancel_{now_datetime().strftime('%H%M%S%f')}"
	frappe.db.savepoint(savepoint)
	try:
		if booking_name:
			_lock_service_booking_row(booking_name)
		_lock_service_appointment_rows([appointment.name])
		appointment = frappe.get_doc("Service Appointment", appointment.name)
		result = _cancel_service_appointment_without_commit(appointment, cancellation_reasons)
		frappe.db.commit()  # nosemgrep - cancellation is an explicit Desk action boundary.
		return result
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _cancel_couple_from_desk(appointment, cancellation_reasons=None, cancel_both: bool = True):
	from frappoint.frappoint.services.booking_transaction_service import (
		release_couple_appointment_allocations,
	)

	appointment_name = appointment.name
	linked_name = appointment.couple_appointment_id
	booking_name = appointment.booking_id
	savepoint = f"couple_cancel_{now_datetime().strftime('%H%M%S%f')}"
	frappe.db.savepoint(savepoint)
	try:
		if booking_name:
			_lock_service_booking_row(booking_name)
		_lock_service_appointment_rows([appointment_name, linked_name])
		appointment = frappe.get_doc("Service Appointment", appointment_name)
		linked = frappe.get_doc("Service Appointment", linked_name)
		if (
			appointment.couple_appointment_id != linked.name
			or linked.couple_appointment_id != appointment.name
		):
			frappe.throw(_("The linked couple appointment is not reciprocal."))
		if cancel_both:
			ordered = sorted(
				[appointment, linked], key=lambda row: (not bool(row.is_primary_in_couple), row.name)
			)
			release_couple_appointment_allocations(
				appointment_names=[row.name for row in ordered],
				target_status="Cancelled",
			)
			results = [
				_cancel_service_appointment_without_commit(
					row,
					cancellation_reasons,
					capacity_already_released=True,
					queue_calendar_sync=False,
				)
				for row in ordered
			]
			_queue_couple_calendar_sync(ordered, event_status="Cancelled")
		else:
			# The user explicitly chose to keep the other service. It becomes a normal single appointment.
			frappe.db.set_value(
				"Service Appointment",
				appointment.name,
				{"couple_appointment_id": None, "is_primary_in_couple": 0},
				update_modified=False,
			)
			frappe.db.set_value(
				"Service Appointment",
				linked.name,
				{"couple_appointment_id": None, "is_primary_in_couple": 0},
				update_modified=False,
			)
			appointment.couple_appointment_id = None
			appointment.is_primary_in_couple = 0
			appointment.reload()
			results = [_cancel_service_appointment_without_commit(appointment, cancellation_reasons)]

		frappe.db.commit()  # nosemgrep - the selected couple cancellation is one action boundary.
		return {
			"success": True,
			"cancelledBoth": cancel_both,
			"cancelledAppointments": [row.get("appointment") for row in results],
			"remainingAppointment": None if cancel_both else linked.name,
			"message": _("Both couple appointments were cancelled.")
			if cancel_both
			else _("The selected appointment was cancelled and the other appointment was kept."),
		}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _edit_couple_from_desk(
	appointment,
	new_appointment_date=None,
	new_start_time=None,
	new_end_time=None,
	new_provider=None,
	new_slot_ids=None,
	new_service_unit=None,
	couple_update=None,
):
	"""Move/reassign both draft appointments under one allocation savepoint."""
	from frappoint.frappoint.services.booking_transaction_service import (
		release_couple_appointment_allocations,
		reserve_couple_appointment_allocations,
	)

	appointment_name = appointment.name
	linked_name = appointment.couple_appointment_id
	booking_name = appointment.booking_id
	update = _parse_json_payload(couple_update, {}) or {}
	if not isinstance(update, dict):
		frappe.throw(_("Couple update must be an object."))
	legs = [
		_payload_value(update, "guest_1", "guest1", "primary", default={}) or {},
		_payload_value(update, "guest_2", "guest2", "secondary", default={}) or {},
	]
	if not all(isinstance(leg, dict) for leg in legs):
		frappe.throw(_("Each couple update entry must be an object."))

	savepoint = f"couple_edit_{now_datetime().strftime('%H%M%S%f')}"
	frappe.db.savepoint(savepoint)
	try:
		if booking_name:
			_lock_service_booking_row(booking_name)
		_lock_service_appointment_rows([appointment_name, linked_name])
		appointment = frappe.get_doc("Service Appointment", appointment_name)
		linked = frappe.get_doc("Service Appointment", linked_name)
		if (
			appointment.couple_appointment_id != linked.name
			or linked.couple_appointment_id != appointment.name
		):
			frappe.throw(_("The linked couple appointment is not reciprocal."))
		if appointment.docstatus != 0 or linked.docstatus != 0:
			frappe.throw(
				_("Submitted couple appointments must use the couple reschedule action."),
				title=_("Couple Reschedule Required"),
			)
		primary = appointment if appointment.is_primary_in_couple else linked
		secondary = linked if appointment.is_primary_in_couple else appointment
		ordered = [primary, secondary]
		common_date = (
			_payload_value(
				update, "date", "appointment_date", "appointmentDate", default=new_appointment_date
			)
			or appointment.appointment_date
		)
		common_start = (
			_payload_value(update, "start_time", "startTime", default=new_start_time)
			or appointment.start_time
		)
		release_couple_appointment_allocations(
			appointment_names=[row.name for row in ordered], target_status="Released"
		)
		for row, leg in zip(ordered, legs, strict=True):
			is_target = row.name == appointment.name
			row.flags.allow_couple_update = True
			row.flags.skip_couple_validation = True
			row.flags.skip_resource_allocation = True
			row.flags.skip_capacity_validation = True
			row.flags.skip_couple_auto_confirmation = True
			row.appointment_date = common_date
			row.start_time = common_start
			row.appointment_provider = (
				_provider_reference(_payload_value(leg, "provider", "provider_id", "providerId"))
				or (new_provider if is_target else None)
				or row.appointment_provider
			)
			row.service_unit = (
				_payload_value(leg, "service_unit", "serviceUnit")
				or (new_service_unit if is_target else None)
				or row.service_unit
			)

			leg_end_time = _payload_value(leg, "end_time", "endTime")
			if not leg_end_time and is_target and new_end_time:
				leg_end_time = new_end_time
			expected_end_time = (
				get_datetime(f"{common_date} {common_start}") + timedelta(minutes=cint(row.duration))
			).time()
			if leg_end_time and get_time(leg_end_time) != expected_end_time:
				frappe.throw(
					_("Appointment {0}'s end time must match its service duration.").format(row.name)
				)
			row.end_time = expected_end_time

			leg_slot_ids = _payload_value(leg, "slot_ids", "slotIds")
			if leg_slot_ids is None and is_target:
				leg_slot_ids = new_slot_ids
			if leg_slot_ids is not None:
				if isinstance(leg_slot_ids, list):
					row.selected_slot_ids = json.dumps(leg_slot_ids) if leg_slot_ids else None
				else:
					row.selected_slot_ids = leg_slot_ids
			else:
				row.selected_slot_ids = None
			row.save(ignore_permissions=True)

		for row in ordered:
			row.flags.skip_couple_validation = False
			row.validate_provider_offers_service()
			row.validate_couple_configuration()
		_validate_couple_members_against_projector(
			_appointment_as_couple_member(primary),
			_appointment_as_couple_member(secondary),
		)

		reserve_couple_appointment_allocations(
			appointments=[_couple_reservation_request(row) for row in ordered]
		)
		_queue_couple_calendar_sync(ordered)
		frappe.db.commit()  # nosemgrep - both schedule/resource changes are persisted together.
		return {
			"success": True,
			"message": _("Both couple appointments were updated successfully."),
			"updatedAppointments": [row.name for row in ordered],
		}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _new_rescheduled_couple_appointment(old, common_date, common_start, leg, is_target, args):
	end_time = _payload_value(leg, "end_time", "endTime")
	if not end_time and is_target:
		end_time = args.get("new_end_time")
	expected_end_time = (
		get_datetime(f"{common_date} {common_start}") + timedelta(minutes=cint(old.duration))
	).time()
	if end_time and get_time(end_time) != expected_end_time:
		frappe.throw(_("Appointment {0}'s end time must match its service duration.").format(old.name))
	end_time = expected_end_time
	provider = (
		_provider_reference(_payload_value(leg, "provider", "provider_id", "providerId"))
		or (args.get("new_provider") if is_target else None)
		or old.appointment_provider
	)
	service_unit = (
		_payload_value(leg, "service_unit", "serviceUnit")
		or (args.get("new_service_unit") if is_target else None)
		or old.service_unit
	)
	slot_ids = _payload_value(leg, "slot_ids", "slotIds")
	if slot_ids is None and is_target:
		slot_ids = args.get("new_slot_ids")

	new_appointment = frappe.get_doc(
		{
			"doctype": "Service Appointment",
			"booking_id": old.booking_id,
			"customer": old.customer,
			"full_name": old.full_name,
			"mobile_no": old.mobile_no,
			"email": old.email,
			"company": old.company,
			"appointment_type": old.appointment_type,
			"appointment_provider": provider,
			"appointment_date": common_date,
			"start_time": common_start,
			"end_time": end_time,
			"duration": old.duration,
			"service_unit": service_unit,
			"appointment_price": old.appointment_price,
			"total_amount": old.total_amount,
			"grand_total": old.grand_total,
			"currency": old.currency,
			"details": old.details,
			"notes": (old.notes or "") + f"\n\nRescheduled from: {old.name}",
			"status": "Open",
			"source": old.source,
			"add_video_conferencing": old.add_video_conferencing,
			"rescheduled_from": old.name,
			"selected_slot_ids": (
				json.dumps(slot_ids) if isinstance(slot_ids, list) and slot_ids else slot_ids
			),
			"buffer_before_minutes": old.buffer_before_minutes,
			"buffer_after_minutes": old.buffer_after_minutes,
		}
	)
	for guest in old.guests or []:
		new_appointment.append(
			"guests",
			{
				"full_name": guest.full_name,
				"email": guest.email,
				"mobile_no": guest.mobile_no,
				"is_primary": guest.is_primary,
				"notes": guest.notes,
			},
		)
	new_appointment.flags.skip_resource_allocation = True
	new_appointment.flags.skip_calendar_event = True
	new_appointment.flags.skip_couple_validation = True
	new_appointment.flags.skip_capacity_validation = True
	new_appointment.flags.skip_couple_auto_confirmation = True
	new_appointment.flags.allow_couple_update = True
	new_appointment.insert(ignore_permissions=True)
	return new_appointment


def _transfer_rescheduled_appointment_payments(old, new) -> dict:
	payment_rows = frappe.get_all(
		"Service Appointment Payment",
		filters={
			"reference_doctype": "Service Appointment",
			"reference_docname": old.name,
		},
		fields=["name", "amount", "payment_received"],
	)
	paid_amount = 0
	for row in payment_rows:
		if row.get("payment_received"):
			paid_amount += flt(row.get("amount"))
		frappe.db.set_value("Service Appointment Payment", row.get("name"), {"reference_docname": new.name})

	reference_rows = frappe.get_all(
		"Service Appointment Payment Reference",
		filters={
			"reference_doctype": "Service Appointment",
			"reference_name": old.name,
		},
		fields=["name", "allocated_amount"],
	)
	allocated_paid_amount = 0
	for row in reference_rows:
		allocated_paid_amount += flt(row.get("allocated_amount"))
		frappe.db.set_value(
			"Service Appointment Payment Reference", row.get("name"), {"reference_name": new.name}
		)

	old_paid_amount = max(0, flt(old.grand_total) - flt(old.outstanding_amount))
	paid_amount = max(paid_amount, allocated_paid_amount, old_paid_amount)
	grand_total = flt(new.grand_total or new.total_amount)
	new.outstanding_amount = max(0, grand_total - paid_amount)
	if new.outstanding_amount <= 0 and grand_total > 0:
		new.payment_status = "Paid"
	elif paid_amount > 0:
		new.payment_status = "Partly Paid"
	else:
		new.payment_status = "Unpaid"
	frappe.db.set_value(
		"Service Appointment",
		new.name,
		{
			"outstanding_amount": new.outstanding_amount,
			"payment_status": new.payment_status,
		},
		update_modified=False,
	)
	return {
		"payments": len(payment_rows),
		"payment_references": len(reference_rows),
	}


def _reschedule_couple_from_desk(
	appointment,
	new_appointment_date=None,
	new_start_time=None,
	new_end_time=None,
	new_provider=None,
	new_slot_ids=None,
	new_service_unit=None,
	couple_update=None,
):
	from frappoint.frappoint.services.booking_transaction_service import (
		release_couple_appointment_allocations,
		reserve_couple_appointment_allocations,
	)

	appointment_name = appointment.name
	linked_name = appointment.couple_appointment_id
	booking_name = appointment.booking_id
	update = _parse_json_payload(couple_update, {}) or {}
	if not isinstance(update, dict):
		frappe.throw(_("Couple update must be an object."))
	legs = [
		_payload_value(update, "guest_1", "guest1", "primary", default={}) or {},
		_payload_value(update, "guest_2", "guest2", "secondary", default={}) or {},
	]
	args = {
		"new_end_time": new_end_time,
		"new_provider": new_provider,
		"new_slot_ids": new_slot_ids,
		"new_service_unit": new_service_unit,
	}
	savepoint = f"couple_reschedule_{now_datetime().strftime('%H%M%S%f')}"
	frappe.db.savepoint(savepoint)
	try:
		if booking_name:
			_lock_service_booking_row(booking_name)
		_lock_service_appointment_rows([appointment_name, linked_name])
		appointment = frappe.get_doc("Service Appointment", appointment_name)
		linked = frappe.get_doc("Service Appointment", linked_name)
		if (
			appointment.couple_appointment_id != linked.name
			or linked.couple_appointment_id != appointment.name
		):
			frappe.throw(_("The linked couple appointment is not reciprocal."))
		for row in (appointment, linked):
			if row.docstatus != 1:
				frappe.throw(_("Both couple appointments must be submitted before they can be rescheduled."))
			if row.status in {"Cancelled", "Closed", "No Show", "Completed"}:
				frappe.throw(
					_("Appointment {0} cannot be rescheduled in its current state.").format(row.name)
				)
		primary = appointment if appointment.is_primary_in_couple else linked
		secondary = linked if appointment.is_primary_in_couple else appointment
		ordered_old = [primary, secondary]
		common_date = (
			_payload_value(
				update, "date", "appointment_date", "appointmentDate", default=new_appointment_date
			)
			or appointment.appointment_date
		)
		common_start = (
			_payload_value(update, "start_time", "startTime", default=new_start_time)
			or appointment.start_time
		)
		if get_datetime(f"{common_date} {common_start}") < now_datetime():
			frappe.throw(_("Cannot reschedule to a time in the past"))
		new_appointments = [
			_new_rescheduled_couple_appointment(
				old,
				common_date,
				common_start,
				leg,
				old.name == appointment.name,
				args,
			)
			for old, leg in zip(ordered_old, legs, strict=True)
		]
		new_primary, new_secondary = new_appointments
		frappe.db.set_value(
			"Service Appointment",
			new_primary.name,
			{"couple_appointment_id": new_secondary.name, "is_primary_in_couple": 1},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Appointment",
			new_secondary.name,
			{"couple_appointment_id": new_primary.name, "is_primary_in_couple": 0},
			update_modified=False,
		)
		new_primary.couple_appointment_id = new_secondary.name
		new_primary.is_primary_in_couple = 1
		new_secondary.couple_appointment_id = new_primary.name
		new_secondary.is_primary_in_couple = 0

		for old, row in zip(ordered_old, new_appointments, strict=True):
			row.coupon_code = old.coupon_code
			row.discount_amount = old.discount_amount
			row.grand_total = old.grand_total
			frappe.db.set_value(
				"Service Appointment",
				row.name,
				{
					"coupon_code": old.coupon_code,
					"discount_amount": old.discount_amount,
					"grand_total": old.grand_total,
				},
				update_modified=False,
			)
			row.flags.skip_couple_validation = False
			row.validate_provider_offers_service()
			row.validate_couple_configuration()

		release_couple_appointment_allocations(
			appointment_names=[row.name for row in ordered_old], target_status="Released"
		)
		_validate_couple_members_against_projector(
			_appointment_as_couple_member(new_primary),
			_appointment_as_couple_member(new_secondary),
		)
		reserve_couple_appointment_allocations(
			appointments=[_couple_reservation_request(row) for row in new_appointments]
		)

		transfer_summary = []
		for old, new in zip(ordered_old, new_appointments, strict=True):
			transfer_summary.append(_transfer_rescheduled_appointment_payments(old, new))
		# Keep the reschedule savepoint intact. Pair confirmation owns a nested,
		# distinct savepoint so a later failure while cancelling either old member
		# can still roll the entire reschedule back to its original boundary.
		confirmation_savepoint = f"{savepoint}_confirmation"
		new_primary._confirm_couple_appointments(savepoint=confirmation_savepoint)
		new_primary.reload()
		new_secondary.reload()

		for old, new in zip(ordered_old, new_appointments, strict=True):
			old.add_comment(
				"Comment",
				_("Couple appointment rescheduled to {0} at {1}. New appointment: {2}").format(
					frappe.format(common_date, {"fieldtype": "Date"}), new.start_time, new.name
				),
			)
			old.flags.ignore_permissions = True
			old.flags.ignore_links = True
			old.flags.is_rescheduling = True
			old.flags.allow_couple_lifecycle = True
			old.flags.skip_capacity_release = True
			old.flags.skip_calendar_status_sync = True
			old.cancel()
			old.db_set("status", "Rescheduled")
			old.db_set("rescheduled_to", new.name)
		_queue_couple_calendar_sync(new_appointments)
		_queue_couple_calendar_sync(ordered_old, event_status="Cancelled")

		frappe.db.commit()  # nosemgrep - both replacements and both cancellations are atomic.
		return {
			"success": True,
			"new_appointments": [row.name for row in new_appointments],
			"old_appointments": [row.name for row in ordered_old],
			"new_appointment": (new_primary.name if appointment.is_primary_in_couple else new_secondary.name),
			"transferred_payments": sum(row["payments"] for row in transfer_summary),
			"transferred_payment_references": sum(row["payment_references"] for row in transfer_summary),
			"message": _("Both couple appointments were rescheduled successfully."),
		}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


@frappe.whitelist()
def perform_appointment_action(
	appointment_id: str | None = None,
	action: str | None = None,
	new_appointment_date: str | None = None,
	new_start_time: str | None = None,
	new_end_time: str | None = None,
	new_provider: str | None = None,
	new_slot_ids: str | list | None = None,
	new_service_unit: str | None = None,
	actual_start_time: str | None = None,
	actual_end_time: str | None = None,
	cancellation_reasons: str | list | None = None,
	cancel_couple: int | str | bool | None = None,
	couple_update: str | dict | None = None,
	**kwargs,
):
	appointment_id = (
		appointment_id
		or kwargs.get("appointment")
		or kwargs.get("appointment_name")
		or kwargs.get("appointmentId")
	)
	action = action or kwargs.get("action")
	new_appointment_date = new_appointment_date or kwargs.get("newAppointmentDate")
	new_start_time = new_start_time or kwargs.get("newStartTime")
	new_end_time = new_end_time or kwargs.get("newEndTime")
	new_provider = new_provider or kwargs.get("newProvider") or kwargs.get("target_provider")
	new_slot_ids = new_slot_ids if new_slot_ids is not None else kwargs.get("newSlotIds")
	new_service_unit = new_service_unit or kwargs.get("newServiceUnit") or kwargs.get("target_service_unit")
	actual_start_time = actual_start_time or kwargs.get("actualStartTime") or kwargs.get("handover_time")
	actual_end_time = actual_end_time or kwargs.get("actualEndTime")
	cancellation_reasons = (
		cancellation_reasons if cancellation_reasons is not None else kwargs.get("cancellationReasons")
	)
	if cancel_couple is None:
		cancel_couple = kwargs.get("cancelCouple")
	couple_update = couple_update if couple_update is not None else kwargs.get("coupleUpdate")

	if not appointment_id:
		frappe.throw(_("Appointment reference is required."))
	if not action:
		frappe.throw(_("Action is required."))

	action = action.strip().lower()
	appointment = frappe.get_doc("Service Appointment", appointment_id)

	if isinstance(new_slot_ids, str):
		try:
			parsed_slot_ids = json.loads(new_slot_ids)
			if isinstance(parsed_slot_ids, list):
				new_slot_ids = parsed_slot_ids
		except Exception:
			pass

	if action in {"check_in", "start", "pause", "resume"}:
		apply_appointment_event_action(
			appointment,
			action,
			action_time=actual_start_time or now_datetime(),
		)
		appointment.reload()
		frappe.db.commit()  # nosemgrep - event action must be visible before the updated desk response.
		return _build_appointment_response(
			appointment,
			(frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None),
		)

	if action == "complete":
		apply_appointment_event_action(
			appointment,
			"complete",
			action_time=actual_end_time or now_datetime(),
		)
		appointment.complete_appointment()
		appointment.reload()
		frappe.db.commit()  # nosemgrep - completion updates booking and appointment state for the response.
		return _build_appointment_response(
			appointment,
			(frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None),
		)

	if action == "confirm":
		if appointment.couple_appointment_id and not appointment.is_primary_in_couple:
			appointment = frappe.get_doc("Service Appointment", appointment.couple_appointment_id)
		appointment.confirm_appointment()
		appointment.reload()
		frappe.db.commit()  # nosemgrep - confirmation is an explicit desk action boundary.
		return _build_appointment_response(
			appointment,
			(frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None),
		)

	if action == "cancel":
		if appointment.couple_appointment_id and cancel_couple is None:
			booking = (
				frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
			)
			response = _build_appointment_response(appointment, booking)
			response["operationResult"] = {
				"success": False,
				"requiresCoupleConfirmation": True,
				"appointment": appointment.name,
				"coupleAppointment": appointment.couple_appointment_id,
				"message": _("This is a couple booking. Do you want to cancel both appointments?"),
			}
			return response

		if appointment.couple_appointment_id:
			result = _cancel_couple_from_desk(
				appointment,
				cancellation_reasons=cancellation_reasons,
				cancel_both=_is_truthy(cancel_couple),
			)
		else:
			result = _cancel_single_from_desk(appointment, cancellation_reasons=cancellation_reasons)
		appointment.reload()
		booking = (
			frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
		)
		response = _build_appointment_response(appointment, booking)
		response["operationResult"] = result
		return response

	if action in {"reassign_provider", "edit_time_slot"}:
		if appointment.couple_appointment_id and (
			action == "edit_time_slot" or new_provider or new_service_unit or couple_update
		):
			if appointment.status in {"Checked In", "In Progress"}:
				frappe.throw(
					_("An active couple booking cannot be reassigned or moved independently."),
					title=_("Couple Update Required"),
				)
			result = _edit_couple_from_desk(
				appointment,
				new_appointment_date=new_appointment_date,
				new_start_time=new_start_time,
				new_end_time=new_end_time,
				new_provider=new_provider,
				new_slot_ids=new_slot_ids,
				new_service_unit=new_service_unit,
				couple_update=couple_update,
			)
			appointment.reload()
			booking = (
				frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
			)
			response = _build_appointment_response(appointment, booking)
			response["providerChangeOptions"] = []
			response["operationResult"] = result
			return response

		if action == "reassign_provider":
			if appointment.status in {"Checked In", "In Progress"}:
				if new_provider:
					result = reassign_ongoing_appointment(
						appointment_name=appointment_id,
						target_provider=new_provider,
						handover_time=actual_start_time,
					)
					appointment.reload()
					booking = (
						frappe.get_doc("Service Booking", appointment.booking_id)
						if appointment.booking_id
						else None
					)
					response = _build_appointment_response(appointment, booking)
					response["providerChangeOptions"] = []
					response["operationResult"] = result
					return response

				result = get_ongoing_reassignment_options(
					appointment_name=appointment_id,
					handover_time=actual_start_time,
				)
				booking = (
					frappe.get_doc("Service Booking", appointment.booking_id)
					if appointment.booking_id
					else None
				)
				response = _build_appointment_response(appointment, booking)
				response["providerChangeOptions"] = result.get("provider_change_options") or []
				response["operationResult"] = result
				return response

			# Allocation-first path: provider/service unit updates are provider-option driven.
			if new_provider or new_service_unit:
				result = change_appointment_provider(
					appointment_id,
					target_provider=new_provider or appointment.appointment_provider,
					target_service_unit=new_service_unit or appointment.service_unit,
				)
				appointment.reload()
				booking = (
					frappe.get_doc("Service Booking", appointment.booking_id)
					if appointment.booking_id
					else None
				)
				response = _build_appointment_response(appointment, booking)
				response["providerChangeOptions"] = []
				response["operationResult"] = result
				return response

			provider_change_options = _get_allocation_provider_change_options(appointment)
			result = {
				"success": True,
				"appointment": appointment.name,
				"current_provider": appointment.appointment_provider,
				"provider_change_options": provider_change_options,
			}

			# Fallback for legacy slot-backed appointments where projector options are empty.
			if not provider_change_options:
				try:
					result = change_appointment_provider(appointment_id)
					provider_change_options = result.get("provider_change_options") or []
				except Exception:
					provider_change_options = []

			booking = (
				frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
			)
			response = _build_appointment_response(appointment, booking)
			response["providerChangeOptions"] = provider_change_options
			response["operationResult"] = result
			return response

		# Booking desk frequently operates on non-submitted appointments; allow in-place updates.
		if not new_appointment_date:
			new_appointment_date = appointment.appointment_date
		if not new_start_time:
			new_start_time = appointment.start_time
		if not new_end_time:
			new_end_time = appointment.end_time

		appointment.appointment_date = new_appointment_date
		appointment.start_time = new_start_time
		appointment.end_time = new_end_time
		appointment.appointment_provider = new_provider or appointment.appointment_provider
		appointment.service_unit = new_service_unit or appointment.service_unit
		if new_slot_ids is not None:
			if isinstance(new_slot_ids, list):
				appointment.selected_slot_ids = json.dumps(new_slot_ids) if new_slot_ids else None
			else:
				appointment.selected_slot_ids = new_slot_ids

		appointment.save(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep - desk time-slot edits must be persisted before returning.
		booking = (
			frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
		)
		response = _build_appointment_response(appointment, booking)
		response["operationResult"] = {
			"success": True,
			"message": _("Appointment updated successfully."),
			"updated_appointment": appointment.name,
		}
		return response

	if action == "reschedule":
		if not new_appointment_date:
			new_appointment_date = appointment.appointment_date
		if not new_start_time:
			new_start_time = appointment.start_time
		if not new_end_time:
			new_end_time = appointment.end_time
		normalized_new_slot_ids = None
		if isinstance(new_slot_ids, list):
			normalized_new_slot_ids = json.dumps(new_slot_ids) if new_slot_ids else None
		elif new_slot_ids:
			normalized_new_slot_ids = new_slot_ids

		if appointment.couple_appointment_id:
			result = _reschedule_couple_from_desk(
				appointment,
				new_appointment_date=new_appointment_date,
				new_start_time=new_start_time,
				new_end_time=new_end_time,
				new_provider=new_provider,
				new_slot_ids=normalized_new_slot_ids,
				new_service_unit=new_service_unit,
				couple_update=couple_update,
			)
			new_appointment = frappe.get_doc("Service Appointment", result["new_appointment"])
			booking = (
				frappe.get_doc("Service Booking", new_appointment.booking_id)
				if new_appointment.booking_id
				else None
			)
			response = _build_appointment_response(new_appointment, booking)
			response["operationResult"] = result
			return response

		result = reschedule_appointment(
			appointment_name=appointment_id,
			new_appointment_date=new_appointment_date,
			new_start_time=new_start_time,
			new_end_time=new_end_time,
			new_provider=new_provider or appointment.appointment_provider,
			new_slot_ids=normalized_new_slot_ids,
			new_service_unit=new_service_unit or appointment.service_unit,
		)
		response = {"operationResult": result}
		if result.get("new_appointment"):
			new_appointment = frappe.get_doc("Service Appointment", result["new_appointment"])
			booking = (
				frappe.get_doc("Service Booking", new_appointment.booking_id)
				if new_appointment.booking_id
				else None
			)
			response.update(_build_appointment_response(new_appointment, booking))
		return response

	frappe.throw(_("Unsupported appointment action: {0}").format(action))


def _derive_payment_status(booking_row):
	outstanding = flt(booking_row.get("outstanding_amount"))
	grand_total = flt(booking_row.get("grand_total"))

	if outstanding <= 0:
		return "Paid"
	if grand_total > 0 and outstanding < grand_total:
		return "Partly Paid"
	return "Unpaid"


@frappe.whitelist()
def get_service_bookings_workspace(
	search_text: str | None = None,
	customer_query: str | None = None,
	statuses: str | list | None = None,
	payment_statuses: str | list | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	page: int = 1,
	page_size: int = 20,
):
	statuses = _parse_json_payload(statuses, []) or []
	payment_statuses = _parse_json_payload(payment_statuses, []) or []

	page = max(int(page or 1), 1)
	page_size = max(min(int(page_size or 20), 100), 1)
	limit_start = (page - 1) * page_size

	filters = {"docstatus": ["!=", 2]}
	if statuses:
		filters["status"] = ["in", statuses]

	if from_date and to_date:
		filters["booking_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["booking_date"] = [">=", from_date]
	elif to_date:
		filters["booking_date"] = ["<=", to_date]

	or_filters = []
	if search_text:
		needle = f"%{search_text}%"
		or_filters.extend(
			[
				["name", "like", needle],
				["full_name", "like", needle],
				["customer", "like", needle],
				["mobile_no", "like", needle],
			]
		)

	if customer_query:
		needle = f"%{customer_query}%"
		or_filters.extend(
			[
				["full_name", "like", needle],
				["customer", "like", needle],
				["mobile_no", "like", needle],
			]
		)

	rows = frappe.get_all(
		"Service Booking",
		filters=filters,
		or_filters=or_filters or None,
		fields=[
			"name",
			"status",
			"customer",
			"full_name",
			"mobile_no",
			"email",
			"booking_date",
			"currency",
			"grand_total",
			"outstanding_amount",
		],
		order_by="modified desc",
		limit_start=limit_start,
		limit_page_length=page_size + 1,
	)

	has_more = len(rows) > page_size
	rows = rows[:page_size]

	filtered_rows = []
	for row in rows:
		derived_payment_status = _derive_payment_status(row)
		if payment_statuses and derived_payment_status not in payment_statuses:
			continue
		filtered_rows.append((row, derived_payment_status))

	bookings = []
	for row, payment_status in filtered_rows:
		booking_doc = frappe.get_doc("Service Booking", row.get("name"))
		serialized = _serialize_booking(booking_doc)
		serialized["bookingDate"] = row.get("booking_date")
		serialized["paymentStatus"] = payment_status
		serialized["appointmentCount"] = len(serialized.get("appointments") or [])
		bookings.append(serialized)

	return {
		"bookings": bookings,
		"page": page,
		"pageSize": page_size,
		"hasMore": has_more,
	}


def _get_doctype_latest_modified(doctype: str) -> str:
	table = frappe.qb.DocType(doctype)
	result = frappe.qb.from_(table).select(Max(table.modified)).run()
	latest = result[0][0] if result else None
	return str(latest or "")


@frappe.whitelist()
def get_booking_desk_cache_version():
	return {
		"serviceTypesVersion": _get_doctype_latest_modified("Service Type"),
		"providersVersion": _get_doctype_latest_modified("Service Provider"),
		"customersVersion": _get_doctype_latest_modified("Customer"),
		"bookingsVersion": _get_doctype_latest_modified("Service Booking"),
		"generatedAt": str(now_datetime()),
	}


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
