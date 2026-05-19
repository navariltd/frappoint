import { useCheckoutStore } from "@/stores/checkout.store";
import { PAYMENT_CHANNELS } from "@/types/payment";

export function usePaymentWorkflow() {
	const store = useCheckoutStore();

	const submitPayment = async ({ redirectTo = "" } = {}) => {
		const method = store.selectedMethod;
		if (!method) {
			throw new Error("Select a payment method first.");
		}

		if (store.selectedPaymentChannel === PAYMENT_CHANNELS.ONLINE) {
			if (method.sourceType !== "gateway") {
				throw new Error("Online channel requires a configured payment gateway.");
			}
			return store.triggerGatewayPayment({ redirectTo });
		}

		if (store.selectedPaymentChannel === PAYMENT_CHANNELS.OFFLINE) {
			if (method.sourceType !== "mode_of_payment") {
				throw new Error("Offline channel requires an ERPNext mode of payment.");
			}
			return store.recordManualPayment();
		}

		throw new Error("Select Offline or Online payment channel first.");
	};

	return {
		submitPayment,
	};
}
