<template>
	<!-- <pre>
        {{ JSON.stringify(details, null, 2) }}
    </pre> -->
	<div v-if="modelValue" class="space-y-6">
		<div v-if="!selectedService" class="relative">
			<div class="relative group">
				<span
					class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors"
				>
					search
				</span>
				<input
					v-model="searchQuery"
					@input="debouncedSearch"
					class="w-full pl-12 pr-4 py-4 bg-slate-100 dark:bg-slate-800 border-2 border-transparent rounded-2xl text-sm focus:bg-white focus:ring-4 focus:ring-primary/10 focus:border-primary/20 outline-none transition-all"
					placeholder="Search for a service..."
					type="text"
				/>
			</div>

			<div
				v-if="searchQuery && serviceList.data"
				class="absolute z-50 w-full mt-2 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
			>
				<div v-if="serviceList.loading" class="p-4 text-center text-sm text-slate-500">
					Searching...
				</div>
				<div v-else>
					<button
						v-for="service in serviceList.data.data"
						:key="service.name"
						@click="selectService(service.name)"
						class="w-full flex items-center justify-between px-5 py-4 hover:bg-primary/5 transition-colors border-b border-slate-50 dark:border-slate-800 last:border-0 text-left"
					>
						<div class="flex items-center gap-3">
							<div
								class="size-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400"
							>
								<span class="material-symbols-outlined text-sm">spa</span>
							</div>
							<div>
								<p class="text-sm font-bold text-slate-900 dark:text-white">
									{{ service.appointment_type }}
								</p>
								<p
									class="text-[10px] text-slate-500 uppercase font-bold tracking-tight"
								>
									{{ service.item_group }}
								</p>
							</div>
						</div>
						<span class="material-symbols-outlined text-slate-300 text-sm"
							>chevron_right</span
						>
					</button>
				</div>
			</div>
		</div>

		<div v-else class="animate-in fade-in slide-in-from-bottom-2 duration-300">
			<div
				class="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl mb-6 border border-slate-100 dark:border-slate-700"
			>
				<div class="flex items-center gap-3">
					<div
						class="size-10 rounded-xl bg-primary text-white flex items-center justify-center shadow-lg shadow-primary/20"
					>
						<span class="material-symbols-outlined">spa</span>
					</div>
					<div>
						<h3 class="font-bold text-slate-900 dark:text-white">
							{{ selectedService.appointment_type }}
						</h3>
						<p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
							{{ selectedService.item_group }}
						</p>
					</div>
				</div>
				<button
					@click="resetSelection"
					class="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors flex items-center gap-1 text-xs font-bold"
				>
					<span class="material-symbols-outlined text-sm">edit</span>
					Change
				</button>
			</div>

			<div v-if="details.loading" class="text-center py-10 text-slate-500">
				<div
					class="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"
				></div>
				Loading variants...
			</div>

			<div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div
					v-for="(price, index) in selectedService.prices"
					:key="price.price_name"
					@click="confirmSelection(price)"
					:class="[
						'cursor-pointer p-5 rounded-2xl border-2 transition-all group relative',
						/* Check against price_name */
						selectedPriceId === price.price_name
							? 'border-primary bg-white dark:bg-slate-900 shadow-md ring-4 ring-primary/5'
							: 'border-transparent bg-slate-50 dark:bg-slate-800/50 hover:border-slate-200',
					]"
				>
					<div class="flex justify-between items-center mb-3">
						<span class="font-bold text-slate-900 dark:text-white">{{
							price.price_name
						}}</span>
						<span
							class="material-symbols-outlined text-primary"
							v-if="selectedPriceId === price.price_name"
						>
							check_circle
						</span>
						<span
							class="material-symbols-outlined text-slate-300 group-hover:text-primary transition-colors"
							v-else
						>
							radio_button_unchecked
						</span>
					</div>

					<div class="flex items-center gap-2 text-xs text-slate-500 mb-4">
						<span class="material-symbols-outlined text-[16px]">schedule</span>
						<span>{{ price.duration }} mins</span>
					</div>

					<div class="text-xl font-black text-primary">
						{{ price.currency }} {{ price.amount.toLocaleString() }}
					</div>
				</div>
			</div>
		</div>
	</div>

	<div v-else class="p-8 text-center text-slate-400">Initializing service selection...</div>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import { createResource } from "frappe-ui";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({ price_id: null }),
	},
});
const emit = defineEmits(["update:modelValue"]);

const searchQuery = ref("");
const selectedService = ref(null);

// Local state for UI selection feedback
const selectedPriceId = computed(() => props.modelValue?.price_id);

// Sync local selection if parent changes (e.g., clicking Back/Next)
watch(
	() => props.modelValue?.price_id,
	(val) => {
		selectedPriceId.value = val;
	}
);

// Resource: Search for Service Types
const serviceList = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	auto: false,
});

// Resource: Get full details including prices
const details = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_type_details",
	onSuccess: (data) => {
		selectedService.value = data;
		searchQuery.value = "";
	},
});

// 1. New: Initial Hydration Logic
// This runs when the component loads (like when editing a guest)
watch(
	() => props.modelValue?.appointment_type,
	(newType) => {
		if (newType && !selectedService.value) {
			// If we have a type but no selectedService object, fetch it
			details.submit({ service_type: newType });
		}
	},
	{ immediate: true }
);

function selectService(name) {
	emit("update:modelValue", { ...props.modelValue, price_id: null });
	details.submit({ service_type: name });
}

function resetSelection() {
	selectedService.value = null;
	selectedPriceId.value = null;
	searchQuery.value = "";

	// Tell parent we are clearing the service
	emit("update:modelValue", {
		...props.modelValue,
		price_id: null,
		appointment_type: "",
		service: "",
		duration: 0,
		amount: 0,
	});
}

function confirmSelection(price) {
	// Use price_name since the API doesn't provide 'name'
	const uniqueId = price.price_name;

	emit("update:modelValue", {
		...props.modelValue,
		price_id: uniqueId,
		appointment_type: selectedService.value.appointment_type,
		service: `${price.price_name} ${selectedService.value.appointment_type}`,
		duration: price.duration,
		amount: price.amount,
		currency: price.currency,
	});
}

// Search debounce logic
let timeout;
function debouncedSearch() {
	clearTimeout(timeout);
	timeout = setTimeout(() => {
		if (searchQuery.value.length > 1) {
			serviceList.submit({ search_term: searchQuery.value, page_size: 5 });
		}
	}, 300);
}
</script>
