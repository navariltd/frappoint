import { createResource } from "frappe-ui";

const CREATE_CHECKOUT_PAYMENT_LINK_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.create_checkout_payment_link";

const paymentLinkResource = createResource({
	url: CREATE_CHECKOUT_PAYMENT_LINK_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function createCheckoutPaymentLinkApi({
	bookingId,
	paymentGateway,
	redirectTo,
	phoneNumber,
}) {
	const response = await paymentLinkResource.fetch({
		booking_id: bookingId,
		payment_gateway: paymentGateway || undefined,
		redirect_to: redirectTo || undefined,
		phone_number: phoneNumber || undefined,
	});
	return unwrapPayload(response ?? paymentLinkResource.data);
}
