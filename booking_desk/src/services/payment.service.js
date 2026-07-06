import { createCheckoutPaymentLinkApi } from "@/api/payments.api";

export async function createHostedCheckoutPayment({
	bookingId,
	paymentGateway,
	redirectTo,
	phoneNumber,
	amount,
	paymentType,
}) {
	return createCheckoutPaymentLinkApi({
		bookingId,
		paymentGateway,
		redirectTo,
		phoneNumber,
		amount,
		paymentType,
	});
}
