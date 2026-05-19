import { computed, onMounted, unref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useBookingDetailsStore } from "@/stores/bookingDetails.store";

export function useBookingDetails(bookingId = "") {
	const store = useBookingDetailsStore();
	const refs = storeToRefs(store);
	const bookingIdRef = computed(() => unref(bookingId));

	onMounted(() => {
		store.fetchBooking(bookingIdRef.value);
	});

	watch(bookingIdRef, (value) => {
		if (value) {
			store.fetchBooking(value);
		}
	});

	const summary = computed(() => refs.booking.value);

	return {
		...refs,
		summary,
		financialSummary: computed(() => store.financialSummary),
		summaryMetrics: computed(() => store.summaryMetrics),
		hasBooking: computed(() => store.hasBooking),
		hasAppointments: computed(() => store.hasAppointments),
		retry: () => store.retry(bookingIdRef.value),
	};
}
