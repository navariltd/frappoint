import { computed, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { useServicesStore } from "@/stores/services.store";

export function useServiceCart() {
	const store = useServicesStore();
	const {
		filteredServices,
		categories,
		selectedCategory,
		searchQuery,
		customers,
		selectedCustomerId,
		customerSummary,
		cartItems,
		subtotal,
		taxAmount,
		grandTotal,
		cartCount,
		canContinue,
		isLoadingServices,
		isLoadingCustomers,
		isLoadingCustomerSummary,
		error,
	} = storeToRefs(store);

	const currency = computed(() => {
		const first = cartItems.value[0];
		return first?.currency || "KES";
	});

	const formatMoney = (amount) => {
		return `${currency.value} ${Number(amount || 0).toFixed(2)}`;
	};

	const onAddService = (service, price, packageName, duration, packageId) =>
		store.addServiceToCart(service, price, packageName, duration, packageId);
	const onRemoveService = (serviceId) => store.removeServiceFromCart(serviceId);
	const onDecrementService = (serviceId) => store.decrementServiceQuantity(serviceId);
	const onCategorySelect = (category) => store.setSelectedCategory(category);
	const onSearchChange = (value) => store.setSearchQuery(value);
	const onSelectCustomer = (customerId) => store.setSelectedCustomer(customerId);
	const onResolveServicePackages = (serviceId, preferredDuration) =>
		store.resolveServicePackages(serviceId, preferredDuration);
	const onRetry = () => store.initialize();
	const onClearCart = () => store.clearCart();

	watch(selectedCustomerId, async () => {
		await store.refreshCustomerSummary();
	});

	onMounted(() => {
		store.initialize();
	});

	return {
		filteredServices,
		categories,
		selectedCategory,
		searchQuery,
		customers,
		selectedCustomerId,
		customerSummary,
		cartItems,
		subtotal,
		taxAmount,
		grandTotal,
		cartCount,
		canContinue,
		isLoadingServices,
		isLoadingCustomers,
		isLoadingCustomerSummary,
		error,
		currency,
		formatMoney,
		onAddService,
		onRemoveService,
		onDecrementService,
		onCategorySelect,
		onSearchChange,
		onSelectCustomer,
		onResolveServicePackages,
		onRetry,
		onClearCart,
	};
}
