import { createResource } from "frappe-ui";

const GET_CHECKOUT_PAYMENT_METHODS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_checkout_payment_methods";

const methodsResource = createResource({
	url: GET_CHECKOUT_PAYMENT_METHODS_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function getCheckoutPaymentMethodsApi(bookingId) {
	const response = await methodsResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? methodsResource.data);
}
