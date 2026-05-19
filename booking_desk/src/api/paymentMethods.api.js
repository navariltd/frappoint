import { createResource } from "frappe-ui";

const GET_CHECKOUT_OFFLINE_PAYMENT_METHODS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_checkout_offline_payment_methods";
const GET_CHECKOUT_ONLINE_PAYMENT_GATEWAYS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_checkout_online_payment_gateways";

const offlineMethodsResource = createResource({
	url: GET_CHECKOUT_OFFLINE_PAYMENT_METHODS_ENDPOINT,
	auto: false,
});

const onlineMethodsResource = createResource({
	url: GET_CHECKOUT_ONLINE_PAYMENT_GATEWAYS_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function fetchOfflinePaymentMethodsApi(bookingId) {
	const response = await offlineMethodsResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? offlineMethodsResource.data);
}

export async function fetchOnlinePaymentGatewaysApi(bookingId) {
	const response = await onlineMethodsResource.fetch({ booking_id: bookingId });
	return unwrapPayload(response ?? onlineMethodsResource.data);
}
