import { computed, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { useServicesStore } from "@/stores/services.store";
import { useBookingStore } from "@/stores/bookingStore";
import { useBookingCart } from "@/composables/useBookingCart";

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

	async function onPageChange(page) {
		const nextPage = Number(page);
		if (
			!Number.isInteger(nextPage) ||
			nextPage < 1 ||
			nextPage === servicesStore.filters.page
		) {
			return;
		}

		servicesStore.updateFilters({ page: nextPage });
		await servicesStore.fetchServices();
		window.scrollTo({ top: 0, behavior: "smooth" });
	}

	function openService(service) {
		servicesStore.setSelectedService(service);
		router.push({ name: "ServiceDetails", params: { name: service.name } });
	}

	function addToBooking(service) {
		const { addItem } = useBookingCart();

		// Add service to booking cart with default package
		if (service.price) {
			addItem({
				service_type: service.name,
				service_name: service.appointment_type,
				package_name: service.price.price_name,
				duration_minutes: service.price.duration || service.default_duration_in_minutes || 30,
				price: service.price.amount || 0,
				currency: service.price.currency || "USD",
				image: service.image,
				metadata: {
					item_group: service.item_group,
					item_name: service.item_name,
				},
			});
		}
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
		onPageChange,
		openService,
		addToBooking,
	};
}
