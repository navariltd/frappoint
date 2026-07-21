import { createCheckoutPaymentLinkApi } from "@/api/payments.api";
import { normalizeCheckoutSummary } from "@/services/checkout.service";

export async function createHostedCheckoutPayment({
	bookingId,
	paymentGateway,
	redirectTo,
	phoneNumber,
	amount,
	paymentType,
	couponCode,
	finalAmountReference,
}) {
	const payload = await createCheckoutPaymentLinkApi({
		bookingId,
		paymentGateway,
		redirectTo,
		phoneNumber,
		amount,
		paymentType,
		couponCode,
		finalAmountReference,
	});
	return {
		...payload,
		checkout: payload?.checkout ? normalizeCheckoutSummary(payload.checkout) : undefined,
	};
}
