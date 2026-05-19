<template>
	<section class="rounded-xl border border-outline-variant bg-surface p-4">
		<h3 class="text-[14px] font-semibold text-on-surface mb-3">Payment Method</h3>
		<div class="grid grid-cols-2 lg:grid-cols-3 gap-2">
			<button
				v-for="method in methods"
				:key="method.id"
				type="button"
				class="rounded-xl border px-3 py-3 text-left"
				:class="
					selectedMethodId === method.id
						? 'border-primary bg-primary/10'
						: 'border-outline-variant bg-surface hover:bg-surface-container-low'
				"
				@click="$emit('update:selectedMethodId', method.id)"
			>
				<div class="flex items-center justify-between gap-2">
					<p class="text-[12px] font-semibold text-on-surface truncate">
						{{ method.name || method.label }}
					</p>
					<p
						v-if="paymentChannel === 'offline' && selectedMethodId === method.id"
						class="text-[11px] font-semibold text-primary whitespace-nowrap"
					>
						{{ formatMoney(payableAmount) }}
					</p>
				</div>
				<p
					v-if="method.type !== 'offline'"
					class="text-[11px] text-on-surface-variant mt-1"
				>
					{{ (method.capabilities || []).join(" • ") || "redirect" }}
				</p>
			</button>
		</div>
	</section>
</template>

<script setup>
const props = defineProps({
	methods: {
		type: Array,
		default: () => [],
	},
	selectedMethodId: {
		type: String,
		default: "",
	},
	paymentChannel: {
		type: String,
		default: "",
	},
	payableAmount: {
		type: Number,
		default: 0,
	},
	currency: {
		type: String,
		default: "KES",
	},
});

defineEmits(["update:selectedMethodId"]);

function formatMoney(amount) {
	return `${props.currency} ${Number(amount || 0).toFixed(2)}`;
}
</script>
