<template>
	<div class="flex h-full overflow-hidden bg-[#f4fafd] text-on-surface">
		<section
			class="flex-1 min-w-0 flex flex-col border-r border-outline-variant/60 bg-surface-container-low"
		>
			<div
				class="shrink-0 px-4 py-3 border-b border-outline-variant bg-surface-container-lowest"
			>
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
					<p class="font-label-md text-label-md font-semibold">Customer</p>

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
							class="w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-[12px] outline-none focus:ring-2 focus:ring-primary"
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
						v-if="isLoadingCustomers || isLoadingCustomerSummary"
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
							<div class="min-w-0">
								<p class="text-[12px] font-semibold truncate">{{ item.name }}</p>
								<p
									v-if="item.packageName"
									class="text-[11px] text-on-surface-variant"
								>
									{{ item.packageName }}
								</p>
								<p class="text-[11px] text-on-surface-variant">
									{{ item.duration }} min • Qty {{ item.quantity }}
								</p>
							</div>
							<p class="text-[12px] font-semibold">
								{{ formatMoney(item.price * item.quantity) }}
							</p>
						</div>
						<div class="mt-2 flex justify-end gap-2">
							<button
								type="button"
								class="text-[11px] text-on-surface-variant"
								@click="onDecrementService(item.cartKey || item.serviceId)"
							>
								-1
							</button>
							<button
								type="button"
								class="text-[11px] text-error"
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
				<div class="space-y-1.5 text-[12px]">
					<div class="flex justify-between">
						<span class="text-on-surface-variant">Subtotal</span>
						<span>{{ formatMoney(subtotal) }}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-on-surface-variant">Tax</span>
						<span>{{ formatMoney(taxAmount) }}</span>
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
						canContinue
							? 'bg-primary text-on-primary'
							: 'bg-surface-container-high text-on-surface-variant cursor-not-allowed'
					"
					:disabled="!canContinue"
				>
					Continue Booking
				</button>
			</div>
		</aside>
	</div>

	<PricingPackageDialog
		:isOpen="isPricingDialogOpen"
		:service="selectedService"
		@select="handlePriceSelected"
		@close="isPricingDialogOpen = false"
	/>
</template>

<script setup>
import { computed, ref } from "vue";
import { useServiceCart } from "@/composables/services/useServiceCart";
import PricingPackageDialog from "@/components/services/PricingPackageDialog.vue";

const customerSearch = ref("");
const isCustomerPickerOpen = ref(false);
const isPricingDialogOpen = ref(false);
const selectedService = ref(null);
const loadingServiceId = ref("");

const {
	filteredServices,
	categories,
	selectedCategory,
	customers,
	selectedCustomerId,
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
	formatMoney,
	onAddService,
	onRemoveService,
	onDecrementService,
	onCategorySelect,
	onSelectCustomer,
	onResolveServicePackages,
	onRetry,
	onClearCart,
} = useServiceCart();

const selectedCustomerName = computed(() => {
	if (!selectedCustomerId.value) {
		return "";
	}
	const selected = customers.value.find((customer) => customer.id === selectedCustomerId.value);
	return selected?.name || "";
});

const filteredCustomers = computed(() => {
	const query = customerSearch.value.trim().toLowerCase();
	if (!query) {
		return customers.value;
	}
	return customers.value.filter((customer) => customer.name.toLowerCase().includes(query));
});

const selectCustomer = (customer) => {
	onSelectCustomer(customer.id);
	customerSearch.value = "";
	isCustomerPickerOpen.value = false;
};

const enableCustomerPicker = () => {
	onSelectCustomer("");
	customerSearch.value = "";
	isCustomerPickerOpen.value = true;
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

const clearCart = onClearCart;
</script>

<style scoped>
.material-symbols-outlined {
	font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
}

.scrollbar-hide::-webkit-scrollbar {
	display: none;
}
</style>
