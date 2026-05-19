import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useBookingsStore } from "@/stores/bookings.store";

export function useBookings() {
	const store = useBookingsStore();
	const refs = storeToRefs(store);

	onMounted(() => {
		store.fetchBookings({ page: 1 });
	});

	const hasBookings = computed(() => refs.bookings.value.length > 0);

	return {
		...refs,
		hasBookings,
		fetchBookings: store.fetchBookings,
		retry: store.retry,
		setView: store.setView,
		setFilters: store.setFilters,
		resetFilters: store.resetFilters,
	};
}
