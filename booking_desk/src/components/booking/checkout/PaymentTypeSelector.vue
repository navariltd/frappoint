<template>
	<section class="rounded-xl border border-outline-variant bg-surface p-4">
		<h3 class="text-[14px] font-semibold text-on-surface mb-3">Settlement Strategy</h3>
		<div class="inline-flex rounded-xl bg-surface-container p-1">
			<button
				type="button"
				class="px-4 py-2 rounded-lg text-[12px] font-semibold transition-colors"
				:class="
					paymentType === 'full'
						? 'bg-primary-container text-on-primary-container shadow-sm'
						: 'text-on-surface-variant hover:text-on-surface'
				"
				@click="$emit('update:paymentType', 'full')"
			>
				Full Payment
			</button>
			<button
				type="button"
				class="px-4 py-2 rounded-lg text-[12px] font-semibold transition-colors"
				:class="
					paymentType === 'deposit'
						? 'bg-primary-container text-on-primary-container shadow-sm'
						: 'text-on-surface-variant hover:text-on-surface'
				"
				@click="$emit('update:paymentType', 'deposit')"
			>
				Deposit
			</button>
		</div>

		<div v-if="paymentType === 'deposit'" class="mt-4">
			<label class="block text-[12px] text-on-surface-variant mb-1">Deposit Amount</label>
			<input
				type="number"
				min="0"
				step="0.01"
				:value="depositAmount"
				class="w-full rounded-lg border border-outline px-3 py-2 text-[13px]"
				@input="$emit('update:depositAmount', $event.target.value)"
			/>
			<p class="text-[11px] text-on-surface-variant mt-1">
				Minimum due: {{ currency }} {{ minimumDue.toFixed(2) }}
			</p>
		</div>
	</section>
</template>

<script setup>
defineProps({
	paymentType: {
		type: String,
		required: true,
	},
	depositAmount: {
		type: Number,
		default: 0,
	},
	minimumDue: {
		type: Number,
		default: 0,
	},
	currency: {
		type: String,
		default: "KES",
	},
});

defineEmits(["update:paymentType", "update:depositAmount"]);
</script>
