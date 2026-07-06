<template>
	<div v-if="isOpen" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
		<div
			class="bg-surface-container-lowest rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
		>
			<div
				class="p-6 border-b border-outline-variant sticky top-0 bg-surface-container-lowest"
			>
				<h2 class="text-lg font-semibold">Select Package</h2>
				<p class="text-[12px] text-on-surface-variant mt-1">{{ service.name }}</p>
			</div>

			<div class="p-6 space-y-3">
				<button
					v-for="price in service.availablePrices"
					:key="price.id"
					type="button"
					class="w-full rounded-xl border border-outline-variant p-4 text-left transition-colors hover:bg-surface-container-low active:bg-surface-container-high"
					@click="selectPrice(price)"
				>
					<div class="flex items-start justify-between">
						<div class="flex-1">
							<p class="font-semibold text-[13px]">{{ price.name }}</p>
							<p
								v-if="price.pricingModel"
								class="text-[11px] text-on-surface-variant mt-1 uppercase"
							>
								{{ price.pricingModel }}
							</p>
							<p
								v-if="price.duration"
								class="text-[12px] text-on-surface-variant mt-1"
							>
								{{ price.duration }} min
							</p>
							<p
								v-if="price.guestCount"
								class="text-[12px] text-on-surface-variant mt-1"
							>
								Up to {{ price.guestCount }} guest(s)
							</p>
						</div>
						<p class="font-semibold text-[13px] text-primary">
							{{ formatCurrency(price.amount, price.currency) }}
						</p>
					</div>
				</button>
			</div>

			<div
				class="sticky bottom-0 p-6 border-t border-outline-variant bg-surface-container-lowest"
			>
				<button
					type="button"
					class="w-full rounded-xl px-4 py-3 bg-surface-container-high text-on-surface font-medium transition-colors hover:bg-outline-variant"
					@click="close"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	isOpen: Boolean,
	service: {
		type: Object,
		default: () => ({}),
	},
});

const emit = defineEmits(["select", "close"]);

const selectPrice = (price) => {
	emit("select", price);
	close();
};

const close = () => {
	emit("close");
};

function formatCurrency(value, currency, locale = "en-US") {
	return new Intl.NumberFormat(locale, {
		style: "currency",
		currency: currency,
		minimumFractionDigits: 2,
	}).format(value);
}
</script>
