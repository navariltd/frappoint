import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Max
from frappe.utils import flt, now_datetime

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
			"selected_slot_ids",
		],
		order_by="creation asc",
	)
	provider_ids = [row.appointment_provider for row in appointments if row.get("appointment_provider")]
	provider_names = _get_provider_name_map(provider_ids)

	return {
		"name": booking.name,
		"status": booking.status,
		"customer": booking.customer,
		"fullName": booking.full_name,
		"email": booking.email,
		"mobileNo": booking.mobile_no,
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
				"slotIds": [],
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
		"bookingId": appointment.booking_id,
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
		"grandTotal": flt(appointment.grand_total or appointment.total_amount),
		"outstandingAmount": flt(appointment.outstanding_amount),
		"details": appointment.details,
		"notes": appointment.notes,
		"source": appointment.source,
		"selectedSlotIds": [],
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
	paid_amount = sum(flt(payment.get("amount")) for payment in payments if payment.get("paymentReceived"))
	outstanding_amount = flt(appointment_payload.get("outstandingAmount"))
	if outstanding_amount <= 0 and flt(appointment_payload.get("totalAmount")) > 0:
		payment_status = "Paid"
	elif paid_amount > 0:
		payment_status = "Partly Paid"
	else:
		payment_status = appointment_payload.get("paymentStatus") or "Unpaid"

	appointment_payload["paymentStatus"] = payment_status

	return {
		"appointment": appointment_payload,
		"booking": _serialize_booking(booking) if booking else None,
		"eventLogs": event_logs,
		"timeTracking": time_tracking,
		"payments": payments,
		"paymentSummary": {
			"currency": appointment_payload.get("currency") or (booking.currency if booking else "KES"),
			"totalAmount": flt(appointment_payload.get("totalAmount")),
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
		},
		"coupon": coupon_summary,
	}


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
			"message": _("Coupon code is invalid."),
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

	return {
		"valid": valid,
		"message": (_("Coupon is valid.") if valid else _("Coupon is not applicable to this booking.")),
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
		frappe.throw(_("Coupon code is invalid."))

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
		frappe.throw(_("Coupon is not applicable to this booking."))

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
		frappe.throw(_("Coupon code is invalid."))

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
def upsert_draft_service_appointment(
	booking_id: str | None = None,
	assignment=None,
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
			"slotIds": (json.loads(appointment.selected_slot_ids) if appointment.selected_slot_ids else []),
		},
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


@frappe.whitelist()
def perform_appointment_action(
	appointment_id: str | None = None,
	action: str | None = None,
	new_appointment_date: str | None = None,
	new_start_time: str | None = None,
	new_end_time: str | None = None,
	new_provider: str | None = None,
	new_slot_ids=None,
	new_service_unit: str | None = None,
	actual_start_time: str | None = None,
	actual_end_time: str | None = None,
	cancellation_reasons=None,
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
		frappe.db.commit()
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
		frappe.db.commit()
		return _build_appointment_response(
			appointment,
			(frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None),
		)

	if action == "confirm":
		appointment.confirm_appointment()
		appointment.reload()
		frappe.db.commit()
		return _build_appointment_response(
			appointment,
			(frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None),
		)

	if action == "cancel":
		result = cancel_appointment(appointment_id, cancellation_reasons=cancellation_reasons)
		appointment.reload()
		booking = (
			frappe.get_doc("Service Booking", appointment.booking_id) if appointment.booking_id else None
		)
		response = _build_appointment_response(appointment, booking)
		response["operationResult"] = result
		return response

	if action in {"reassign_provider", "edit_time_slot"}:
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
		frappe.db.commit()
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
	statuses=None,
	payment_statuses=None,
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
