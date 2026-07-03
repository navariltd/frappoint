import { createResource } from "frappe-ui";

// Reuse the same backend endpoints as booking_desk
const GET_CHECKOUT_SUMMARY_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_checkout_summary";
const GET_ONLINE_GATEWAYS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_checkout_online_payment_gateways";
const CREATE_PAYMENT_LINK_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.create_checkout_payment_link";
const VALIDATE_COUPON_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.validate_checkout_coupon";
const APPLY_COUPON_ENDPOINT = "frappoint.frappoint.api.booking_desk.apply_checkout_coupon";
const REMOVE_COUPON_ENDPOINT = "frappoint.frappoint.api.booking_desk.remove_checkout_coupon";

const summaryResource = createResource({ url: GET_CHECKOUT_SUMMARY_ENDPOINT, auto: false });
const gatewaysResource = createResource({ url: GET_ONLINE_GATEWAYS_ENDPOINT, auto: false });
const paymentLinkResource = createResource({ url: CREATE_PAYMENT_LINK_ENDPOINT, auto: false });
const validateCouponResource = createResource({ url: VALIDATE_COUPON_ENDPOINT, auto: false });
const applyCouponResource = createResource({ url: APPLY_COUPON_ENDPOINT, auto: false });
const removeCouponResource = createResource({ url: REMOVE_COUPON_ENDPOINT, auto: false });

const unwrap = (payload: any) => payload?.message ?? payload ?? null;

export async function getCheckoutSummaryApi(bookingId: string) {
	const response = await summaryResource.fetch({ booking_id: bookingId });
	return unwrap(response ?? summaryResource.data);
}

export async function getOnlineGatewaysApi(bookingId: string) {
	const response = await gatewaysResource.fetch({ booking_id: bookingId });
	return unwrap(response ?? gatewaysResource.data);
}

export async function createPaymentLinkApi(params: {
	bookingId: string;
	paymentGateway: string;
	redirectTo?: string;
	phoneNumber?: string;
	amount?: number;
	paymentType?: "full" | "deposit";
	couponCode?: string;
	finalAmountReference?: number;
}) {
	const payload = {
		booking_id: params.bookingId,
		payment_gateway: params.paymentGateway || undefined,
		redirect_to: params.redirectTo || undefined,
		phone_number: params.phoneNumber || undefined,
		amount: params.amount || undefined,
		payment_type: params.paymentType || undefined,
		coupon_code: params.couponCode || undefined,
		final_amount_reference: params.finalAmountReference || undefined,
	};

	const response = await paymentLinkResource.fetch({
		...payload,
	});
	return unwrap(response ?? paymentLinkResource.data);
}

export async function validateCheckoutCouponApi(bookingId: string, couponCode: string) {
	const response = await validateCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode,
	});
	return unwrap(response ?? validateCouponResource.data);
}

export async function applyCheckoutCouponApi(bookingId: string, couponCode: string) {
	const response = await applyCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode,
	});
	return unwrap(response ?? applyCouponResource.data);
}

export async function removeCheckoutCouponApi(bookingId: string, couponCode?: string) {
	const response = await removeCouponResource.fetch({
		booking_id: bookingId,
		coupon_code: couponCode || undefined,
	});
	return unwrap(response ?? removeCouponResource.data);
}
