import { createResource } from "frappe-ui";

const ENDPOINTS = {
	pricingSummary: "frappoint.frappoint.api.service_booking.get_booking_pricing_summary",
	applyBookingCoupon: "frappoint.frappoint.api.booking_desk.apply_checkout_coupon",
	removeBookingCoupon: "frappoint.frappoint.api.booking_desk.remove_checkout_coupon",
	applyAppointmentCoupon: "frappoint.frappoint.api.booking_desk.apply_appointment_coupon",
	removeAppointmentCoupon: "frappoint.frappoint.api.booking_desk.remove_appointment_coupon",
};

const pricingSummaryResource = createResource({ url: ENDPOINTS.pricingSummary, auto: false });
const applyBookingCouponResource = createResource({ url: ENDPOINTS.applyBookingCoupon, auto: false });
const removeBookingCouponResource = createResource({ url: ENDPOINTS.removeBookingCoupon, auto: false });
const applyAppointmentCouponResource = createResource({ url: ENDPOINTS.applyAppointmentCoupon, auto: false });
const removeAppointmentCouponResource = createResource({ url: ENDPOINTS.removeAppointmentCoupon, auto: false });

const unwrap = (payload: any) => {
	if (!payload) return null;

	// Response can either be:
	// 1) { message: {...actual payload...} }
	// 2) { message: "OK", checkout: {...} }
	// 3) { ...actual payload... }
	const candidate = payload?.message ?? payload;

	if (candidate && typeof candidate === "object") return candidate;
	if (payload && typeof payload === "object") return payload;

	return candidate ?? null;
};

export async function getBookingPricingSummaryApi(bookingId: string) {
	const response = await pricingSummaryResource.fetch({ booking_id: bookingId });
	return unwrap(response ?? pricingSummaryResource.data);
}

export async function applyBookingCouponApi(bookingId: string, couponCode: string) {
	const response = await applyBookingCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode,
	});
	return unwrap(response ?? applyBookingCouponResource.data);
}

export async function removeBookingCouponApi(bookingId: string) {
	const response = await removeBookingCouponResource.fetch({ booking_id: bookingId });
	return unwrap(response ?? removeBookingCouponResource.data);
}

export async function applyAppointmentCouponApi(
	bookingId: string,
	appointmentId: string,
	couponCode: string,
) {
	const response = await applyAppointmentCouponResource.fetch({
		booking_id: bookingId,
		appointment_id: appointmentId,
		coupon_code: couponCode,
	});
	return unwrap(response ?? applyAppointmentCouponResource.data);
}

export async function removeAppointmentCouponApi(bookingId: string, appointmentId: string) {
	const response = await removeAppointmentCouponResource.fetch({
		booking_id: bookingId,
		appointment_id: appointmentId,
	});
	return unwrap(response ?? removeAppointmentCouponResource.data);
}

// Keep old names for checkout.store.ts compatibility
export const applyReviewCouponApi = applyBookingCouponApi;
export const removeReviewCouponApi = removeBookingCouponApi;
export const validateReviewCouponApi = async (_bookingId: string, _couponCode: string) => null;
