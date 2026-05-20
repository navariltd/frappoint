<template>
	<section class="space-y-4 border-t border-outline-variant/30 pt-6">
		<div class="flex items-center justify-between gap-4">
			<span class="font-headline-sm text-headline-sm text-on-surface">Total</span>
			<span class="font-headline-md text-headline-md font-bold text-primary">{{
				totalLabel
			}}</span>
		</div>

		<p v-if="selectedPackage" class="text-label-sm text-on-surface-variant/80">
			{{ selectedPackage.price_name || selectedPackage.name }} ·
			{{ selectedPackage.duration }} min
		</p>
		<p v-else class="text-label-sm text-on-surface-variant/70">
			Select a package to continue.
		</p>

		<button
			type="button"
			class="w-full rounded-full px-8 py-4 font-headline-sm text-headline-sm text-white transition-all shadow-lg shadow-primary/20 disabled:cursor-not-allowed disabled:bg-surface-container-high disabled:text-on-surface-variant"
			:class="
				selectedPackage
					? 'bg-primary hover:bg-primary/90 active:scale-[0.98]'
					: 'bg-surface-container-high'
			"
			:disabled="busy || !selectedPackage"
			@click="$emit('add')"
		>
			{{ busy ? "Adding..." : "Add to Booking" }}
		</button>

		<p class="text-center text-label-sm text-on-surface-variant/70">
			You’ll choose the date, provider, and payment step later in the booking flow.
		</p>

		<p v-if="error" class="text-center text-label-sm text-red-700">{{ error }}</p>
	</section>
</template>

<script setup>
import { computed } from "vue";
import { formatCurrency } from "@/utils";

const props = defineProps({
	selectedPackage: {
		type: Object,
		default: null,
	},
	service: {
		type: Object,
		default: () => ({}),
	},
	busy: {
		type: Boolean,
		default: false,
	},
	error: {
		type: String,
		default: "",
	},
});

defineEmits(["add"]);

const totalLabel = computed(() => {
	if (!props.selectedPackage) {
		return "--";
	}

	return formatCurrency(props.selectedPackage.amount, props.selectedPackage.currency);
});
</script>
