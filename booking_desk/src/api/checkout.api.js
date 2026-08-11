import { createResource } from "frappe-ui";

const GET_CHECKOUT_SUMMARY_ENDPOINT = "frappoint.frappoint.api.booking_desk.get_checkout_summary";
const RECORD_MANUAL_PAYMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.record_manual_checkout_payment";
const CONFIRM_WITHOUT_PAYMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.confirm_checkout_without_payment";
const VALIDATE_COUPON_ENDPOINT = "frappoint.frappoint.api.booking_desk.validate_checkout_coupon";
const APPLY_COUPON_ENDPOINT = "frappoint.frappoint.api.booking_desk.apply_checkout_coupon";
const REMOVE_COUPON_ENDPOINT = "frappoint.frappoint.api.booking_desk.remove_checkout_coupon";

const checkoutSummaryResource = createResource({
	url: GET_CHECKOUT_SUMMARY_ENDPOINT,
	auto: false,
});

const manualPaymentResource = createResource({
	url: RECORD_MANUAL_PAYMENT_ENDPOINT,
	auto: false,
});

const confirmWithoutPaymentResource = createResource({
	url: CONFIRM_WITHOUT_PAYMENT_ENDPOINT,
	auto: false,
});

const validateCouponResource = createResource({
	url: VALIDATE_COUPON_ENDPOINT,
	auto: false,
});

const applyCouponResource = createResource({
	url: APPLY_COUPON_ENDPOINT,
	auto: false,
});

const removeCouponResource = createResource({
	url: REMOVE_COUPON_ENDPOINT,
	auto: false,
});

const hasPayloadShape = (payload) =>
	payload &&
	typeof payload === "object" &&
	("valid" in payload ||
		"booking" in payload ||
		"payment" in payload ||
		"checkout" in payload ||
		"confirmedAppointments" in payload ||
		"paymentName" in payload);

const unwrapPayload = (...candidates) => {
	for (const candidate of candidates) {
		let payload = candidate;
		for (let depth = 0; depth < 4; depth += 1) {
			if (payload == null) break;
			if (hasPayloadShape(payload)) return payload;
			if (
				typeof payload === "object" &&
				Object.prototype.hasOwnProperty.call(payload, "message")
			) {
				payload = payload.message;
				continue;
			}
			return payload;
		}
	}
	return null;
};

export async function getCheckoutSummaryApi(bookingId) {
	const response = await checkoutSummaryResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response, checkoutSummaryResource.data);
}

export async function recordManualCheckoutPaymentApi({
	bookingId,
	amount,
	modeOfPayment,
	referenceNo,
}) {
	const response = await manualPaymentResource.fetch({
		booking_id: bookingId,
		amount,
		mode_of_payment: modeOfPayment || undefined,
		reference_no: referenceNo || undefined,
	});
	return unwrapPayload(response, manualPaymentResource.data);
}

export async function confirmCheckoutWithoutPaymentApi(bookingId) {
	const response = await confirmWithoutPaymentResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response, confirmWithoutPaymentResource.data);
}

export async function validateCheckoutCouponApi(bookingId, couponCode) {
	const response = await validateCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode,
	});
	return unwrapPayload(response, validateCouponResource.data);
}

export async function applyCheckoutCouponApi(bookingId, couponCode) {
	const response = await applyCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode,
	});
	return unwrapPayload(response, applyCouponResource.data);
}

export async function removeCheckoutCouponApi(bookingId, couponCode) {
	const response = await removeCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode || undefined,
	});
	return unwrapPayload(response, removeCouponResource.data);
}
