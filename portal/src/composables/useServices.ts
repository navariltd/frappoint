import { computed, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { useServicesStore } from "@/stores/services.store";
import { useBookingStore } from "@/stores/bookingStore";

export function useServices() {
	const servicesStore = useServicesStore();
	const bookingStore = useBookingStore();
	const router = useRouter();
	const refs = storeToRefs(servicesStore);

	let searchDebounce;

	function updateAndFetch(patch = {}, { debounce = 0 } = {}) {
		servicesStore.updateFilters({ ...patch, page: 1 });
		if (debounce > 0) {
			clearTimeout(searchDebounce);
			searchDebounce = setTimeout(() => {
				servicesStore.fetchServices();
			}, debounce);
			return;
		}
		servicesStore.fetchServices();
	}

	function onSearchChange(value) {
		updateAndFetch({ search: value }, { debounce: 250 });
	}

	function onDateChange(value) {
		servicesStore.updateFilters({ date: value });
	}

	function onGuestsChange(value) {
		servicesStore.updateFilters({ guests: Number(value || 1) });
	}

	function onToggleCategory(category) {
		if (!category) {
			return;
		}
		const current = servicesStore.filters.categories || [];
		const exists = current.includes(category);
		const next = exists ? current.filter((item) => item !== category) : [...current, category];
		updateAndFetch({ categories: next });
	}

	function onClearCategories() {
		updateAndFetch({ categories: [] });
	}

	function onDurationChange(duration) {
		const next = servicesStore.filters.duration === duration ? null : duration;
		updateAndFetch({ duration: next });
	}

	function onPriceChange(maxPrice) {
		updateAndFetch({ maxPrice: Number(maxPrice) }, { debounce: 150 });
	}

	function removeFilterChip(chip) {
		if (chip.type === "search") {
			return onSearchChange("");
		}
		if (chip.type === "category") {
			return onToggleCategory(chip.value);
		}
		if (chip.type === "duration") {
			return onDurationChange(chip.value);
		}
		if (chip.type === "date") {
			servicesStore.updateFilters({ date: "" });
			return;
		}
		if (chip.type === "guests") {
			servicesStore.updateFilters({ guests: 1 });
		}
	}

	function clearFilters() {
		servicesStore.clearFilters();
		servicesStore.fetchServices();
	}

	function openService(service) {
		servicesStore.setSelectedService(service);
		router.push({ name: "ServiceDetails", params: { name: service.name } });
	}

	function addToBooking(service) {
		servicesStore.setSelectedService(service);
		bookingStore.setServiceType(service.name);
		if (service.price) {
			bookingStore.setPriceName(service.price.price_name);
			bookingStore.setPrice(service.price.amount);
			bookingStore.setCurrency(service.price.currency);
			bookingStore.setDuration(service.price.duration);
		}
		bookingStore.setNumberOfGuests(servicesStore.filters.guests || 1);
		router.push({ name: "BookingWizard", params: { serviceType: service.name } });
	}

	onBeforeUnmount(() => {
		clearTimeout(searchDebounce);
	});

	return {
		...refs,
		initialize: servicesStore.initialize,
		onSearchChange,
		onDateChange,
		onGuestsChange,
		onToggleCategory,
		onClearCategories,
		onDurationChange,
		onPriceChange,
		removeFilterChip,
		clearFilters,
		openService,
		addToBooking,
	};
}
