<template>
	<div class="flex h-full overflow-hidden text-on-surface">
		<section
			class="flex-1 min-w-0 flex flex-col border-r border-outline-variant/60 bg-surface-container-low"
		>
			<div class="shrink-0 px-4 py-3 border-outline-variant bg-surface-container-lowest">
				<div class="mb-3">
					<div class="relative">
						<span
							class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
							>search</span
						>
						<input
							v-model="searchQuery"
							type="text"
							placeholder="Search services by name"
							class="w-full rounded-xl border border-outline-variant bg-surface-container-low pl-10 pr-3 py-2 text-[12px] outline-none focus:ring-2 focus:ring-secondary"
						/>
					</div>
				</div>
				<div class="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1">
					<button
						v-for="category in categories"
						:key="category"
						type="button"
						class="px-3 py-1.5 rounded-full text-[12px] font-medium whitespace-nowrap border transition-colors"
						:class="
							selectedCategory === category
								? 'bg-primary text-on-primary border-primary'
								: 'bg-surface-container-high text-on-surface border-outline-variant hover:bg-primary-container hover:text-on-primary-container'
						"
						@click="onCategorySelect(category)"
					>
						{{ category }}
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto px-4 py-4">
				<div
					v-if="error"
					class="mb-4 rounded-xl border border-error-container bg-error-container/30 px-3 py-2 text-[12px] flex items-center justify-between"
				>
					<span>{{ error }}</span>
					<button type="button" class="text-primary font-semibold" @click="onRetry">
						Retry
					</button>
				</div>
				<div v-if="isLoadingServices" class="text-[12px] text-on-surface-variant">
					Loading services...
				</div>
				<div
					v-else-if="!filteredServices.length"
					class="rounded-2xl border border-outline-variant bg-surface p-8 text-center text-[13px] text-on-surface-variant"
				>
					No services found for the current search/filter.
				</div>
				<div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
					<article
						v-for="service in filteredServices"
						:key="service.id"
						class="rounded-2xl border border-outline-variant bg-surface-container-lowest p-4 shadow-sm"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<p class="font-label-md text-label-md font-semibold truncate">
									{{ service.name }}
								</p>
								<p class="mt-1 text-[12px] text-on-surface-variant line-clamp-2">
									{{ service.description }}
								</p>
							</div>
							<span
								class="text-[11px] px-2 py-1 rounded-full bg-surface-container-high text-on-surface-variant whitespace-nowrap"
							>
								{{ service.category }}
							</span>
						</div>
						<div class="mt-4 flex items-center justify-between">
							<div class="text-[12px] text-on-surface-variant">
								<p>{{ service.duration }} min</p>
								<p class="font-semibold text-on-surface">
									{{ service.currency }} {{ Number(service.price).toFixed(2) }}
								</p>
							</div>
							<button
								type="button"
								class="w-9 h-9 rounded-full bg-primary text-on-primary flex items-center justify-center transition-transform disabled:opacity-70 disabled:cursor-wait"
								@click="handleAddService(service)"
								:disabled="loadingServiceId === service.id"
								aria-label="Add service"
							>
								<span
									class="material-symbols-outlined text-[18px]"
									:class="loadingServiceId === service.id ? 'animate-spin' : ''"
								>
									{{
										loadingServiceId === service.id
											? "progress_activity"
											: "add"
									}}
								</span>
							</button>
						</div>
					</article>
				</div>
			</div>
		</section>

		<aside class="w-[360px] shrink-0 bg-surface-container-lowest flex flex-col">
			<div class="p-5 space-y-4 shrink-0">
				<section class="space-y-2">
					<div class="flex items-center justify-between gap-2">
						<p class="font-label-md text-label-md font-semibold">Customer</p>
						<button
							type="button"
							class="inline-flex items-center gap-1 rounded-full border border-outline-variant bg-surface-container-low px-2.5 py-1 text-[11px] font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-60 disabled:cursor-wait"
							:disabled="isLoadingCustomerResults"
							@click="onManualRefreshCustomers"
							aria-label="Refresh customers"
						>
							<span class="material-symbols-outlined text-[14px]">
								{{ isLoadingCustomerResults ? "progress_activity" : "refresh" }}
							</span>
							<span>Refresh</span>
						</button>
					</div>

					<div
						v-if="selectedCustomerName && !isCustomerPickerOpen"
						class="w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-[12px] flex items-center justify-between gap-2"
					>
						<span class="truncate">{{ selectedCustomerName }}</span>
						<button
							type="button"
							class="material-symbols-outlined text-[16px] text-on-surface-variant hover:text-on-surface"
							@click="enableCustomerPicker"
							aria-label="Change customer"
						>
							close
						</button>
					</div>

					<div v-else class="relative">
						<input
							v-model="customerSearch"
							type="text"
							placeholder="Search and select customer"
							class="w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-[12px] outline-none focus:ring-2 focus:ring-secondary"
							@focus="isCustomerPickerOpen = true"
						/>
						<div
							v-if="isCustomerPickerOpen"
							class="absolute z-50 mt-1 w-full max-h-44 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-high shadow-lg"
						>
							<button
								v-for="customer in filteredCustomers"
								:key="customer.id"
								type="button"
								class="w-full text-left px-3 py-2 text-[12px] hover:bg-surface-container-low"
								@click="selectCustomer(customer)"
							>
								{{ customer.name }}
							</button>
							<p
								v-if="!filteredCustomers.length"
								class="px-3 py-2 text-[12px] text-on-surface-variant"
							>
								No customers found
							</p>
						</div>
					</div>

					<p
						v-if="isLoadingCustomerResults || isLoadingCustomerSummary"
						class="text-[11px] text-on-surface-variant"
					>
						Refreshing customer list...
					</p>
				</section>
			</div>

			<section class="flex-1 min-h-0 px-5 pb-4">
				<div class="flex items-center justify-between mb-3">
					<span class="text-[11px] text-on-surface-variant"
						>{{ cartCount }} item(s)</span
					>
				</div>
				<div
					v-if="!cartItems.length"
					class="text-[12px] text-on-surface-variant py-6 text-center border border-dashed border-outline-variant rounded-xl"
				>
					No services added yet.
				</div>
				<div v-else class="space-y-2 h-full overflow-y-auto pr-1">
					<div
						v-for="item in cartItems"
						:key="item.cartKey || item.serviceId"
						class="rounded-xl border border-outline-variant p-3 bg-surface-container-low"
					>
						<div class="flex items-start justify-between gap-2">
							<div class="min-w-0 flex-1">
								<p class="text-[12px] font-semibold truncate">{{ item.name }}</p>
								<button
									type="button"
									class="inline-flex items-center gap-1 mt-1.5 text-[11px] font-semibold text-primary bg-primary/10 hover:bg-primary/20 px-2 py-0.5 rounded-full transition-colors"
									@click="openPackageChangeDialog(item)"
								>
									<span class="material-symbols-outlined text-[12px]"
										>swap_horiz</span
									>
									{{ item.packageName || "Change package" }}
								</button>
								<p class="text-[11px] text-on-surface-variant mt-1">
									{{ item.duration }} min
								</p>
							</div>
							<p class="text-[12px] font-semibold whitespace-nowrap">
								{{ formatMoney(item.price * item.quantity) }}
							</p>
						</div>
						<div class="mt-3 flex items-center justify-between gap-2">
							<div
								class="flex items-center gap-2 bg-surface-container-high rounded-lg px-2 py-1"
							>
								<button
									type="button"
									class="text-[13px] text-on-surface hover:text-primary transition-colors"
									@click="onDecrementService(item.cartKey || item.serviceId)"
									:disabled="item.quantity <= 1"
									:class="
										item.quantity <= 1 ? 'opacity-50 cursor-not-allowed' : ''
									"
								>
									−
								</button>
								<span class="text-[12px] font-semibold w-6 text-center">
									{{ item.quantity }}
								</span>
								<button
									type="button"
									class="text-[13px] text-on-surface hover:text-primary transition-colors"
									@click="onIncrementService(item.cartKey || item.serviceId)"
								>
									+
								</button>
							</div>
							<button
								type="button"
								class="text-[11px] text-error hover:text-error/80 transition-colors"
								@click="onRemoveService(item.cartKey || item.serviceId)"
							>
								Remove
							</button>
						</div>
					</div>
				</div>
			</section>

			<div
				class="shrink-0 p-5 border-t border-outline-variant bg-surface-container-lowest space-y-3"
			>
				<div
					v-if="bookingError"
					class="rounded-xl border border-error-container bg-error-container/30 px-3 py-2 text-[12px] text-on-surface"
				>
					{{ bookingError }}
				</div>
				<div class="space-y-1.5 text-[12px]">
					<div class="flex justify-between">
						<span class="text-on-surface-variant">Subtotal</span>
						<span>{{ formatMoney(subtotal) }}</span>
					</div>
					<div
						class="flex justify-between pt-2 border-t border-outline-variant font-semibold text-[13px]"
					>
						<span>Grand Total</span>
						<span>{{ formatMoney(grandTotal) }}</span>
					</div>
				</div>
				<button
					type="button"
					class="w-full rounded-xl px-4 py-3 font-label-md text-label-md transition-colors"
					:class="
						canContinue && !isCreatingBooking
							? 'bg-primary text-on-primary'
							: 'bg-surface-container-high text-on-surface-variant cursor-not-allowed'
					"
					:disabled="!canContinue || isCreatingBooking"
					@click="proceedToGuestAssignment"
				>
					{{ isCreatingBooking ? "Creating Draft Booking..." : "Continue Booking" }}
				</button>
			</div>
		</aside>
	</div>

	<PricingPackageDialog
		:isOpen="isPricingDialogOpen"
		:service="selectedService"
		@select="
			editingCartItemKey ? handleCartPackageSelected($event) : handlePriceSelected($event)
		"
		@close="
			editingCartItemKey
				? onPricingDialogClose()
				: ((isPricingDialogOpen = false), (selectedService = null))
		"
	/>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useBookingWorkflow } from "@/composables/booking/useBookingWorkflow";
import { useServiceCart } from "@/composables/services/useServiceCart";
import PricingPackageDialog from "@/components/services/PricingPackageDialog.vue";
import { searchNormalizedCustomers } from "@/services/services.service";

const router = useRouter();
const customerSearch = ref("");
const customerResults = ref([]);
const isCustomerPickerOpen = ref(false);
const isLoadingCustomerResults = ref(false);
const isPricingDialogOpen = ref(false);
const selectedService = ref(null);
const loadingServiceId = ref("");
const editingCartItemKey = ref("");
const cartItemPackages = ref({});
let customerSearchTimer = null;
let customerSearchToken = 0;

const {
	filteredServices,
	categories,
	selectedCategory,
	searchQuery,
	selectedCustomer,
	customerSummary,
	cartItems,
	subtotal,
	grandTotal,
	cartCount,
	canContinue,
	isLoadingServices,
	isLoadingCustomerSummary,
	error,
	formatMoney,
	onAddService,
	onRemoveService,
	onDecrementService,
	onIncrementService,
	onUpdateServicePackage,
	onCategorySelect,
	onSelectCustomer,
	onResolveServicePackages,
	onRetry,
} = useServiceCart();
const { isCreatingBooking, bookingError, createDraftBookingSession, clearBookingError } =
	useBookingWorkflow();

const selectedCustomerName = computed(() => {
	if (!selectedCustomer.value) {
		return "";
	}
	return selectedCustomer.value.name || "";
});

const filteredCustomers = computed(() => {
	return customerResults.value;
});

const fetchCustomerResults = async (query = "") => {
	const token = ++customerSearchToken;
	isLoadingCustomerResults.value = true;
	try {
		const results = await searchNormalizedCustomers(query, 50);
		if (token === customerSearchToken) {
			customerResults.value = results;
		}
	} finally {
		if (token === customerSearchToken) {
			isLoadingCustomerResults.value = false;
		}
	}
};

const refreshCustomerResults = async () => {
	await fetchCustomerResults(customerSearch.value);
};

const scheduleCustomerSearch = (query) => {
	clearTimeout(customerSearchTimer);
	customerSearchTimer = setTimeout(() => {
		fetchCustomerResults(query);
	}, 250);
};

watch(customerSearch, (value) => {
	if (!isCustomerPickerOpen.value) {
		return;
	}
	scheduleCustomerSearch(value);
});

const selectCustomer = (customer) => {
	onSelectCustomer(customer);
	customerSearch.value = "";
	isCustomerPickerOpen.value = false;
};

const enableCustomerPicker = async () => {
	await fetchCustomerResults("");
	onSelectCustomer("");
	customerSearch.value = "";
	isCustomerPickerOpen.value = true;
};

const onManualRefreshCustomers = async () => {
	await refreshCustomerResults();
};

const handleAddService = async (service) => {
	if (loadingServiceId.value) {
		return;
	}

	loadingServiceId.value = service.id;

	try {
		const packageData = await onResolveServicePackages(service.id, service.duration);
		const packages = packageData?.packages || [];

		if (packages.length > 1) {
			selectedService.value = {
				...service,
				availablePrices: packages,
			};
			isPricingDialogOpen.value = true;
			return;
		}

		if (packages.length === 1) {
			const singlePackage = packages[0];
			onAddService(
				service,
				singlePackage.amount,
				singlePackage.name,
				singlePackage.duration || service.duration,
				singlePackage.id
			);
			return;
		}

		onAddService(
			service,
			service.price,
			"",
			service.duration,
			service.defaultPackageId || "default"
		);
	} finally {
		loadingServiceId.value = "";
	}
};

const handlePriceSelected = (selectedPrice) => {
	if (selectedService.value) {
		onAddService(
			selectedService.value,
			selectedPrice.amount,
			selectedPrice.name,
			selectedPrice.duration || selectedService.value.duration,
			selectedPrice.id
		);
		selectedService.value = null;
	}
};

const openPackageChangeDialog = async (item) => {
	if (!editingCartItemKey.value) {
		editingCartItemKey.value = item.cartKey || item.serviceId;
		const packageData = await onResolveServicePackages(item.serviceId, item.duration);
		cartItemPackages.value[editingCartItemKey.value] = packageData?.packages || [];

		selectedService.value = {
			...item,
			id: item.serviceId,
			availablePrices: cartItemPackages.value[editingCartItemKey.value],
		};
		isPricingDialogOpen.value = true;
	}
};

const handleCartPackageSelected = (selectedPrice) => {
	if (editingCartItemKey.value && selectedService.value) {
		onUpdateServicePackage(
			editingCartItemKey.value,
			selectedPrice.id,
			selectedPrice.name,
			selectedPrice.amount,
			selectedPrice.duration || selectedService.value.duration
		);
		editingCartItemKey.value = "";
		selectedService.value = null;
	}
};

const onPricingDialogClose = () => {
	if (editingCartItemKey.value) {
		editingCartItemKey.value = "";
		handleCartPackageSelected(selectedService.value);
	} else {
		isPricingDialogOpen.value = false;
		selectedService.value = null;
	}
};

const proceedToGuestAssignment = () => {
	if (!canContinue.value) {
		return;
	}
	clearBookingError();
	createDraftBookingSession({
		customer: selectedCustomer.value,
		customerSummary: customerSummary.value,
		cartItems: cartItems.value,
	})
		.then(() => {
			router.push({ name: "GuestAssignment" });
		})
		.catch(() => null);
};
</script>

<style scoped>
.material-symbols-outlined {
	font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
}

.scrollbar-hide::-webkit-scrollbar {
	display: none;
}
</style>
