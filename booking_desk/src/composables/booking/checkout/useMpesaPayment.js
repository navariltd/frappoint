import { onBeforeUnmount, ref } from "vue";
import { useCheckoutStore } from "@/stores/checkout.store";

export function useMpesaPayment() {
	const store = useCheckoutStore();
	const pollingId = ref(null);

	const stopPolling = () => {
		if (pollingId.value) {
			window.clearInterval(pollingId.value);
			pollingId.value = null;
		}
	};

	const startPolling = ({ intervalMs = 8000, onConfirmed = null } = {}) => {
		stopPolling();
		pollingId.value = window.setInterval(async () => {
			await store.refreshSummary();
			if (Number(store.summary.payment.outstandingAmount || 0) <= 0) {
				store.paymentProgress = "success";
				store.statusMessage = "Payment confirmed.";
				stopPolling();
				if (typeof onConfirmed === "function") {
					await onConfirmed();
				}
			}
		}, intervalMs);
	};

	onBeforeUnmount(() => {
		stopPolling();
	});

	return {
		startPolling,
		stopPolling,
	};
}
