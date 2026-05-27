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
		selectedCustomerRecord: null,
		customerSummary: createEmptyCustomerSummary(),
		cartItems: [],
		isLoadingServices: false,
		isLoadingCustomers: false,
		isLoadingCustomerSummary: false,
		error: null,
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
					String(service.name || "")
						.toLowerCase()
						.includes(query);
				return categoryMatch && queryMatch;
			});
		},
		subtotal(state) {
			return state.cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
		},
		grandTotal() {
			return this.subtotal;
		},
		cartCount(state) {
			return state.cartItems.reduce((sum, item) => sum + item.quantity, 0);
		},
		canContinue() {
			return this.cartCount > 0;
		},
		selectedCustomer(state) {
			if (state.selectedCustomerRecord) {
				return state.selectedCustomerRecord;
			}
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
		setSelectedCustomer(customer) {
			if (customer && typeof customer === "object") {
				this.selectedCustomerId = customer.id || "";
				this.selectedCustomerRecord = {
					id: customer.id || "",
					name: customer.name || customer.customer_name || customer.id || "",
				};
				return;
			}

			this.selectedCustomerId = customer || "";
			this.selectedCustomerRecord = null;
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
				this.customers = await fetchNormalizedCustomers(100);
				if (!this.selectedCustomerId && this.customers.length) {
					this.selectedCustomerId = this.customers[0].id;
					this.selectedCustomerRecord = this.customers[0];
				} else if (this.selectedCustomerId && !this.selectedCustomerRecord) {
					this.selectedCustomerRecord =
						this.customers.find((item) => item.id === this.selectedCustomerId) || null;
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
				const selected =
					this.selectedCustomer ||
					this.customers.find((item) => item.id === this.selectedCustomerId);
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
