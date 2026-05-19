<template>
	<div class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<p class="text-[13px] font-semibold text-on-surface">Cash / Manual Settlement</p>
		<div>
			<label class="block text-[12px] text-on-surface-variant mb-1">Amount Tendered</label>
			<input
				type="number"
				min="0"
				step="0.01"
				:value="amountTendered"
				class="w-full rounded-lg border border-outline px-3 py-2 text-[13px]"
				@input="$emit('update:amountTendered', $event.target.value)"
			/>
		</div>
		<div>
			<label class="block text-[12px] text-on-surface-variant mb-1"
				>Reference (optional)</label
			>
			<input
				type="text"
				:value="referenceNo"
				class="w-full rounded-lg border border-outline px-3 py-2 text-[13px]"
				placeholder="Receipt / POS reference"
				@input="$emit('update:referenceNo', $event.target.value)"
			/>
		</div>
		<p class="text-[11px] text-on-surface-variant">
			Change due: {{ currency }} {{ changeDue.toFixed(2) }}
		</p>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	amountTendered: { type: Number, default: 0 },
	referenceNo: { type: String, default: "" },
	payableAmount: { type: Number, default: 0 },
	currency: { type: String, default: "KES" },
});

defineEmits(["update:amountTendered", "update:referenceNo"]);

const changeDue = computed(() =>
	Math.max(0, Number(props.amountTendered || 0) - props.payableAmount)
);
</script>
