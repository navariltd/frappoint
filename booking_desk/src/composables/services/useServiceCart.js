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
		selectedCustomer,
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
	const onRemoveService = (cartKey) => store.removeServiceFromCart(cartKey);
	const onDecrementService = (cartKey) => store.decrementServiceQuantity(cartKey);
	const onIncrementService = (cartKey) => store.incrementServiceQuantity(cartKey);
	const onUpdateServicePackage = (cartKey, packageId, packageName, price, duration) =>
		store.updateServicePackage(cartKey, packageId, packageName, price, duration);
	const onCategorySelect = (category) => store.setSelectedCategory(category);
	const onSearchChange = (value) => store.setSearchQuery(value);
	const onSelectCustomer = (customerId) => store.setSelectedCustomer(customerId);
	const onRefreshCustomers = () => store.loadCustomers();
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
		selectedCustomer,
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
		onIncrementService,
		onUpdateServicePackage,
		onCategorySelect,
		onSearchChange,
		onSelectCustomer,
		onRefreshCustomers,
		onResolveServicePackages,
		onRetry,
		onClearCart,
	};
}
