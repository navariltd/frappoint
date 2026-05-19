import { createCheckoutPaymentLinkApi } from "@/api/payments.api";

export async function createHostedCheckoutPayment({
	bookingId,
	paymentGateway,
	redirectTo,
	phoneNumber,
}) {
	return createCheckoutPaymentLinkApi({
		bookingId,
		paymentGateway,
		redirectTo,
		phoneNumber,
	});
}
