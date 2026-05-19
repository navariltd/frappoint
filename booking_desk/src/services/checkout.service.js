import { getCheckoutSummaryApi, recordManualCheckoutPaymentApi } from "@/api/checkout.api";
import { createEmptyCheckoutSummary } from "@/types/checkout";

const parseErrorMessage = (error, fallback) => {
	if (!error) return fallback;

	if (Array.isArray(error?.messages) && error.messages.length) {
		return error.messages.join(" ");
	}

	if (error?._server_messages) {
		try {
			const serverMessages = JSON.parse(error._server_messages);
			if (Array.isArray(serverMessages) && serverMessages.length) {
				const first = JSON.parse(serverMessages[0]);
				if (first?.message) return first.message;
			}
		} catch {
			return String(error._server_messages);
		}
	}

	return error?.message || fallback;
};

export { parseErrorMessage };

export function normalizeCheckoutSummary(payload) {
	const empty = createEmptyCheckoutSummary();
	if (!payload) return empty;

	return {
		booking: {
			...empty.booking,
			...(payload.booking || {}),
			items: Array.isArray(payload?.booking?.items) ? payload.booking.items : [],
			appointments: Array.isArray(payload?.booking?.appointments)
				? payload.booking.appointments
				: [],
		},
		payment: {
			...empty.payment,
			...(payload.payment || {}),
		},
	};
}

export async function fetchCheckoutSummary(bookingId) {
	try {
		const payload = await getCheckoutSummaryApi(bookingId);
		return normalizeCheckoutSummary(payload);
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Checkout summary could not be loaded."));
	}
}

export async function recordManualCheckoutPayment({
	bookingId,
	amount,
	modeOfPayment,
	referenceNo,
}) {
	try {
		const payload = await recordManualCheckoutPaymentApi({
			bookingId,
			amount,
			modeOfPayment,
			referenceNo,
		});
		return {
			paymentName: payload?.paymentName || "",
			checkout: normalizeCheckoutSummary(payload?.checkout),
		};
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Manual payment could not be recorded."));
	}
}
