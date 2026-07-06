import frappe
from frappe import _
from frappe.utils import flt, getdate

BOOKING_LEVEL_APPLICABILITY = {
	"",
	None,
	"Service Booking",
	"Customer",
	"Customer Group",
	"Booking Source",
}
APPOINTMENT_LEVEL_APPLICABILITY = {"Service Type", "Service Appointment"}


def resolve_coupon_doc(code_or_name: str | None):
	if not code_or_name:
		return None

	code_or_name = code_or_name.strip()
	if not code_or_name:
		return None

	if frappe.db.exists("Service Appointment Coupon Code", code_or_name):
		return frappe.get_doc("Service Appointment Coupon Code", code_or_name)

	coupon_name = frappe.db.get_value(
		"Service Appointment Coupon Code",
		{"code": code_or_name},
		"name",
	)
	if coupon_name:
		return frappe.get_doc("Service Appointment Coupon Code", coupon_name)

	return None


def coupon_scope_label(coupon) -> str:
	if not coupon:
		return "none"

	mapping = {
		"Service Type": "appointment",
		"Service Appointment": "appointment",
		"Service Booking": "booking",
		"Customer": "booking",
		"Customer Group": "booking",
		"Booking Source": "booking",
	}
	return mapping.get(coupon.applicable_for, "booking")


def is_booking_level_coupon(coupon) -> bool:
	if not coupon:
		return False
	return coupon.applicable_for in BOOKING_LEVEL_APPLICABILITY


def is_appointment_level_coupon(coupon) -> bool:
	if not coupon:
		return False
	return coupon.applicable_for in APPOINTMENT_LEVEL_APPLICABILITY


def compute_coupon_discount(amount: float, coupon) -> float:
	amount = flt(amount)
	if amount <= 0 or not coupon:
		return 0

	if coupon.discount_type == "Percentage":
		discount = amount * (flt(coupon.discount_value) / 100)
	else:
		discount = flt(coupon.discount_value)

	if coupon.maximum_discount_amount:
		discount = min(discount, flt(coupon.maximum_discount_amount))

	return min(flt(discount), amount)


def _get_booking_appointment_rows(booking):
	return frappe.get_all(
		"Service Appointment",
		filters={
			"booking_id": booking.name,
			"docstatus": ["<", 2],
			"status": ["not in", ["Cancelled", "Closed", "No Show"]],
		},
		fields=[
			"name",
			"appointment_type",
			"appointment_date",
			"start_time",
			"end_time",
			"appointment_provider",
			"status",
			"payment_status",
			"total_amount",
			"discount_amount",
			"grand_total",
			"outstanding_amount",
			"coupon_code",
			"full_name",
			"email",
			"mobile_no",
			"source",
		],
		order_by="creation asc",
	)


def validate_booking_coupon_for_booking(booking, coupon, appointment_rows=None):
	if not coupon:
		return False, _("Coupon code is invalid.")

	if not is_booking_level_coupon(coupon):
		return False, _("Coupon is not valid for booking-level checkout.")

	if coupon.disable:
		return False, _("Coupon is not active")

	booking_date = booking.get("booking_date") or None
	if not booking_date and appointment_rows:
		for row in appointment_rows:
			if row.get("appointment_date"):
				booking_date = row.get("appointment_date")
				break

	if booking_date:
		is_valid, message = coupon.is_within_validity_period(getdate(booking_date))
		if not is_valid:
			return False, message

	is_available, message = coupon.is_usage_available()
	if not is_available:
		return False, message

	if coupon.applicable_for == "Customer":
		if coupon.customer != booking.customer:
			return False, _("Coupon is not valid for this customer")

	if coupon.applicable_for == "Customer Group":
		customer_group = frappe.get_cached_value("Customer", booking.customer, "customer_group")
		if not customer_group or customer_group != coupon.customer_group:
			return False, _("Coupon is not valid for this customer")

	if coupon.applicable_for == "Booking Source":
		sources = {row.get("source") for row in (appointment_rows or []) if row.get("source")}
		if not sources or coupon.booking_source not in sources:
			return False, _("Coupon is not valid for this booking source")

	return True, ""


def calculate_booking_pricing(booking, booking_coupon_code: str | None = None, appointment_rows=None):
	appointment_rows = appointment_rows or _get_booking_appointment_rows(booking)

	subtotal_amount = 0
	appointment_discount_total = 0
	intermediate_total = 0
	appointment_breakdown = []
	appointment_coupons = {}

	for row in appointment_rows:
		base_amount = flt(row.get("total_amount") or 0)
		appointment_discount = flt(row.get("discount_amount") or 0)
		final_amount = flt(row.get("grand_total") or max(base_amount - appointment_discount, 0))
		coupon_code = row.get("coupon_code") or ""

		subtotal_amount += base_amount
		appointment_discount_total += appointment_discount
		intermediate_total += final_amount

		appointment_breakdown.append(
			{
				"appointmentId": row.get("name"),
				"serviceType": row.get("appointment_type"),
				"guestName": row.get("full_name"),
				"date": row.get("appointment_date"),
				"startTime": row.get("start_time"),
				"endTime": row.get("end_time"),
				"provider": row.get("appointment_provider"),
				"status": row.get("status"),
				"paymentStatus": row.get("payment_status"),
				"currency": booking.currency,
				"baseAmount": base_amount,
				"appointmentDiscountAmount": appointment_discount,
				"finalAmount": final_amount,
				"outstandingAmount": flt(row.get("outstanding_amount") or 0),
				"appointmentCouponCode": coupon_code,
			}
		)

		if coupon_code:
			bucket = appointment_coupons.setdefault(
				coupon_code,
				{"coupon": coupon_code, "discountAmount": 0, "appointments": []},
			)
			bucket["discountAmount"] += appointment_discount
			bucket["appointments"].append(
				{
					"appointmentId": row.get("name"),
					"serviceType": row.get("appointment_type"),
					"guestName": row.get("full_name"),
					"totalAmount": base_amount,
					"grandTotal": final_amount,
					"discountAmount": appointment_discount,
				}
			)

	if not appointment_breakdown:
		for item in booking.items:
			amount = flt(item.total_amount)
			subtotal_amount += amount
			intermediate_total += amount

	booking_coupon_code = (booking_coupon_code or booking.get("coupon_code") or "").strip()
	booking_coupon = resolve_coupon_doc(booking_coupon_code)
	booking_coupon_valid = False
	booking_coupon_message = ""
	booking_discount_amount = 0
	applied_booking_coupon = None

	if booking_coupon:
		booking_coupon_valid, booking_coupon_message = validate_booking_coupon_for_booking(
			booking,
			booking_coupon,
			appointment_rows=appointment_rows,
		)
		if booking_coupon_valid:
			minimum_ok, minimum_message = booking_coupon.is_min_order_met(intermediate_total)
			if minimum_ok:
				booking_discount_amount = compute_coupon_discount(intermediate_total, booking_coupon)
				if booking_discount_amount > 0:
					applied_booking_coupon = {
						"name": booking_coupon.name,
						"code": booking_coupon.code,
						"couponType": booking_coupon.coupon_type,
						"discountType": booking_coupon.discount_type,
						"discountValue": flt(booking_coupon.discount_value),
						"maximumDiscountAmount": flt(booking_coupon.maximum_discount_amount or 0),
						"minimumOrderValue": flt(booking_coupon.minimum_order_value or 0),
						"scope": "booking",
						"discountAmount": booking_discount_amount,
					}
				else:
					booking_coupon_message = _("Coupon did not change the booking amount.")
			else:
				booking_coupon_valid = False
				booking_coupon_message = minimum_message

	final_amount = max(0, flt(intermediate_total) - flt(booking_discount_amount))

	return {
		"subtotalAmount": flt(subtotal_amount),
		"appointmentDiscountTotal": flt(appointment_discount_total),
		"intermediateTotal": flt(intermediate_total),
		"bookingDiscountAmount": flt(booking_discount_amount),
		"totalAmount": flt(intermediate_total),
		"finalAmount": flt(final_amount),
		"appointmentBreakdown": appointment_breakdown,
		"appointmentCoupons": list(appointment_coupons.values()),
		"bookingCoupon": applied_booking_coupon,
		"bookingCouponCode": booking_coupon_code,
		"bookingCouponValid": booking_coupon_valid,
		"bookingCouponMessage": booking_coupon_message,
	}


def sync_booking_pricing_fields(booking, pricing=None):
	pricing = pricing or calculate_booking_pricing(booking)
	booking.appointment_discount_total = flt(pricing.get("appointmentDiscountTotal") or 0)
	booking.booking_discount_amount = flt(pricing.get("bookingDiscountAmount") or 0)
	booking.subtotal = flt(pricing.get("subtotalAmount") or 0)
	booking.grand_total = flt(pricing.get("finalAmount") or 0)

	if pricing.get("bookingCoupon"):
		booking.coupon_code = pricing["bookingCoupon"].get("name")
		discount_type = (pricing["bookingCoupon"].get("discountType") or "").strip().lower()
		booking.coupon_discount_type = "percentage" if discount_type == "percentage" else "fixed"
		booking.coupon_discount_amount = flt(pricing["bookingCoupon"].get("discountAmount") or 0)
		booking.coupon_scope = "booking"
		booking.coupon_applied = 1
	else:
		booking.coupon_discount_type = ""
		booking.coupon_discount_amount = 0
		booking.coupon_scope = ""
		booking.coupon_applied = 0

	return pricing


def validate_booking_coupon_assignment(booking, pricing=None):
	coupon_code = (booking.get("coupon_code") or "").strip()
	if not coupon_code:
		return

	pricing = pricing or calculate_booking_pricing(booking, booking_coupon_code=coupon_code)
	booking_coupon = pricing.get("bookingCoupon")
	if booking_coupon:
		return

	coupon = resolve_coupon_doc(coupon_code)
	if not coupon:
		frappe.throw(_("Coupon code is invalid."))

	if not is_booking_level_coupon(coupon):
		frappe.throw(_("Coupon is not valid for booking-level pricing."))

	message = pricing.get("bookingCouponMessage") or _("Coupon is not applicable to this booking.")
	frappe.throw(message)
