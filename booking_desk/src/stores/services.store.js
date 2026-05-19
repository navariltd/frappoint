import { defineStore } from "pinia";
import {
	buildServiceCategories,
	fetchCustomerSummary,
	fetchNormalizedCustomers,
	fetchNormalizedServices,
	fetchServicePackages,
} from "@/services/services.service";

const createEmptyCustomerSummary = () => ({
	id: "",
	name: "No customer selected",
	phone: "-",
	email: "-",
	recentBookingsCount: 0,
	outstandingBalance: 0,
	isVip: false,
});

export const useServicesStore = defineStore("services", {
	state: () => ({
		services: [],
		categories: ["All"],
		selectedCategory: "All",
		searchQuery: "",
		customers: [],
		selectedCustomerId: "",
		customerSummary: createEmptyCustomerSummary(),
		cartItems: [],
		isLoadingServices: false,
		isLoadingCustomers: false,
		isLoadingCustomerSummary: false,
		error: null,
		taxRate: 0.085,
	}),
	getters: {
		filteredServices(state) {
			const query = state.searchQuery.trim().toLowerCase();
			return state.services.filter((service) => {
				const categoryMatch =
					state.selectedCategory === "All" ||
					service.category === state.selectedCategory;
				const queryMatch =
					!query ||
					service.name.toLowerCase().includes(query) ||
					service.description.toLowerCase().includes(query) ||
					service.category.toLowerCase().includes(query);
				return categoryMatch && queryMatch;
			});
		},
		subtotal(state) {
			return state.cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
		},
		taxAmount() {
			return this.subtotal * this.taxRate;
		},
		grandTotal() {
			return this.subtotal + this.taxAmount;
		},
		cartCount(state) {
			return state.cartItems.reduce((sum, item) => sum + item.quantity, 0);
		},
		canContinue() {
			return this.cartCount > 0;
		},
		selectedCustomer(state) {
			return (
				state.customers.find((customer) => customer.id === state.selectedCustomerId) ||
				null
			);
		},
	},
	actions: {
		setSearchQuery(value) {
			this.searchQuery = value;
		},
		setSelectedCategory(category) {
			this.selectedCategory = category;
		},
		setSelectedCustomer(customerId) {
			this.selectedCustomerId = customerId;
		},
		addServiceToCart(service, price, packageName, duration, packageId) {
			const actualPrice = price !== undefined ? price : service.price;
			const actualDuration = duration !== undefined ? duration : service.duration;
			// Create unique key considering both service and package
			const packageKey = packageId || packageName || "default";
			const cartKey = `${service.id}:${packageKey}`;

			const existing = this.cartItems.find((item) => item.cartKey === cartKey);
			if (existing) {
				existing.quantity += 1;
				return;
			}

			this.cartItems.push({
				serviceId: service.id,
				cartKey,
				name: service.name,
				duration: actualDuration,
				price: actualPrice,
				currency: service.currency,
				category: service.category,
				packageName: packageName || null,
				packageId: packageId || null,
				quantity: 1,
			});
		},
		async resolveServicePackages(serviceId, preferredDuration = 0) {
			return fetchServicePackages(serviceId, preferredDuration);
		},
		removeServiceFromCart(cartKeyOrServiceId) {
			this.cartItems = this.cartItems.filter(
				(item) =>
					item.cartKey !== cartKeyOrServiceId && item.serviceId !== cartKeyOrServiceId
			);
		},
		decrementServiceQuantity(cartKeyOrServiceId) {
			const item = this.cartItems.find(
				(entry) =>
					entry.cartKey === cartKeyOrServiceId || entry.serviceId === cartKeyOrServiceId
			);
			if (!item) {
				return;
			}
			if (item.quantity <= 1) {
				this.removeServiceFromCart(item.cartKey || item.serviceId);
				return;
			}
			item.quantity -= 1;
		},
		incrementServiceQuantity(cartKeyOrServiceId) {
			const item = this.cartItems.find(
				(entry) =>
					entry.cartKey === cartKeyOrServiceId || entry.serviceId === cartKeyOrServiceId
			);
			if (item) {
				item.quantity += 1;
			}
		},
		updateServicePackage(cartKeyOrServiceId, packageId, packageName, price, duration) {
			const item = this.cartItems.find(
				(entry) =>
					entry.cartKey === cartKeyOrServiceId || entry.serviceId === cartKeyOrServiceId
			);
			if (item) {
				item.packageId = packageId;
				item.packageName = packageName;
				item.price = price;
				item.duration = duration;
			}
		},
		clearCart() {
			this.cartItems = [];
		},
		async loadServices() {
			this.isLoadingServices = true;
			this.error = null;
			try {
				this.services = await fetchNormalizedServices();
				this.categories = buildServiceCategories(this.services);
			} catch (error) {
				this.error = error?.message || "Failed to load services";
			} finally {
				this.isLoadingServices = false;
			}
		},
		async loadCustomers() {
			this.isLoadingCustomers = true;
			this.error = null;
			try {
				this.customers = await fetchNormalizedCustomers();
				if (!this.selectedCustomerId && this.customers.length) {
					this.selectedCustomerId = this.customers[0].id;
				}
			} catch (error) {
				this.error = error?.message || "Failed to load customers";
			} finally {
				this.isLoadingCustomers = false;
			}
		},
		async refreshCustomerSummary() {
			this.isLoadingCustomerSummary = true;
			this.error = null;
			try {
				const selected = this.customers.find(
					(item) => item.id === this.selectedCustomerId
				);
				this.customerSummary = await fetchCustomerSummary(
					this.selectedCustomerId,
					selected?.name || ""
				);
			} catch (error) {
				this.error = error?.message || "Failed to load customer summary";
				this.customerSummary = createEmptyCustomerSummary();
			} finally {
				this.isLoadingCustomerSummary = false;
			}
		},
		async initialize() {
			await Promise.all([this.loadServices(), this.loadCustomers()]);
			await this.refreshCustomerSummary();
		},
	},
});
