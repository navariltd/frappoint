import { defineStore } from "pinia";
import { fetchServiceTypes, fetchServicePriceRange } from "@/api/services.api";

function defaultFilters() {
	return {
		search: "",
		date: "",
		guests: 1,
		categories: [],
		duration: null,
		minPrice: null,
		maxPrice: null,
		page: 1,
		pageSize: 12,
	};
}

export const useServicesStore = defineStore("services", {
	state: () => ({
		services: [],
		loading: false,
		error: "",
		filters: defaultFilters(),
		pagination: null,
		selectedService: null,
		priceRange: {
			min: 0,
			max: 500,
			currency: "USD",
		},
		hasInitialized: false,
	}),
	getters: {
		filteredServices(state) {
			return state.services.filter((service) => {
				const durationMatch =
					!state.filters.duration ||
					Number(service.default_duration_in_minutes) === Number(state.filters.duration);

				const categoryMatch =
					!state.filters.categories.length ||
					state.filters.categories.includes(service.item_group);

				const search = String(state.filters.search || "").trim().toLowerCase();
				const searchMatch =
					!search ||
					String(service.appointment_type || "").toLowerCase().includes(search) ||
					String(service.short_description || "").toLowerCase().includes(search);

				return durationMatch && categoryMatch && searchMatch;
			});
		},
		availableCategories(state) {
			return Array.from(new Set(state.services.map((service) => service.item_group).filter(Boolean))).sort();
		},
	},
	actions: {
		setSelectedService(service) {
			this.selectedService = service || null;
		},
		updateFilters(patch = {}) {
			this.filters = { ...this.filters, ...patch };
		},
		clearFilters() {
			this.filters = {
				...defaultFilters(),
				minPrice: this.priceRange.min,
				maxPrice: this.priceRange.max,
			};
		},
		async fetchPriceRange() {
			const range = await fetchServicePriceRange();
			this.priceRange = {
				min: Number(range?.min_price || 0),
				max: Number(range?.max_price || 500),
				currency: range?.currency || "USD",
			};

			if (this.filters.minPrice == null) {
				this.filters.minPrice = this.priceRange.min;
			}
			if (this.filters.maxPrice == null) {
				this.filters.maxPrice = this.priceRange.max;
			}
		},
		async fetchServices() {
			this.loading = true;
			this.error = "";

			try {
				const response = await fetchServiceTypes({
					search_term: this.filters.search || undefined,
					page: this.filters.page,
					page_size: this.filters.pageSize,
					min_price: this.filters.minPrice,
					max_price: this.filters.maxPrice,
				});

				this.services = response?.data || [];
				this.pagination = response?.pagination || null;
			} catch (error) {
				this.error = error?.messages?.[0] || error?.message || "Unable to load services.";
			} finally {
				this.loading = false;
			}
		},
		async initialize() {
			if (this.hasInitialized) {
				return;
			}
			await this.fetchPriceRange();
			await this.fetchServices();
			this.hasInitialized = true;
		},
	},
});
