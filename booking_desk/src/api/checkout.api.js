import { createResource } from "frappe-ui";

const GET_CHECKOUT_SUMMARY_ENDPOINT = "frappoint.frappoint.api.booking_desk.get_checkout_summary";
const RECORD_MANUAL_PAYMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.record_manual_checkout_payment";
const CONFIRM_WITHOUT_PAYMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.confirm_checkout_without_payment";

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

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function getCheckoutSummaryApi(bookingId) {
	const response = await checkoutSummaryResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? checkoutSummaryResource.data);
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
	return unwrapPayload(response ?? manualPaymentResource.data);
}

export async function confirmCheckoutWithoutPaymentApi(bookingId) {
	const response = await confirmWithoutPaymentResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? confirmWithoutPaymentResource.data);
}
