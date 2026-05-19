import { computed } from "vue";
import { useBookingsStore } from "@/stores/bookings.store";

export function useBookingFilters() {
	const store = useBookingsStore();

	const filters = computed(() => store.filters);

	const updateSearchText = (value) => {
		store.setFilters({ searchText: value });
	};

	const updateCustomerQuery = (value) => {
		store.setFilters({ customerQuery: value });
	};

	const updateStatuses = (values) => {
		store.setFilters({ statuses: values || [] });
	};

	const updatePaymentStatuses = (values) => {
		store.setFilters({ paymentStatuses: values || [] });
	};

	const updateDateRange = ({ fromDate, toDate }) => {
		store.setFilters({ fromDate: fromDate || "", toDate: toDate || "" });
	};

	const applyFilters = async () => {
		await store.fetchBookings({ page: 1 });
	};

	const reset = async () => {
		store.resetFilters();
		await store.fetchBookings({ page: 1 });
	};

	return {
		filters,
		updateSearchText,
		updateCustomerQuery,
		updateStatuses,
		updatePaymentStatuses,
		updateDateRange,
		applyFilters,
		reset,
	};
}
