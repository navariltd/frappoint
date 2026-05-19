<template>
	<div
		class="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant flex flex-col justify-between gap-3 shadow-[0px_4px_20px_rgba(45,52,54,0.05)]"
	>
		<h3 class="text-[12px] font-semibold uppercase tracking-wider text-outline">
			Booking Value &amp; Scale
		</h3>
		<div class="flex items-center gap-6">
			<div>
				<p class="text-[22px] md:text-[24px] font-bold text-primary">
					{{ currency }} {{ booking.grandTotal.toFixed(2) }}
				</p>
				<p class="text-outline text-[12px]">Estimated Total</p>
			</div>
			<div class="h-10 w-px bg-outline-variant"></div>
			<div>
				<p class="text-[22px] md:text-[24px] font-bold text-on-surface">
					{{ durationLabel }}
				</p>
				<p class="text-outline text-[12px]">Total Duration</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	booking: { type: Object, required: true },
	currency: { type: String, default: "KES" },
});

const durationLabel = computed(() => {
	const minutes = (props.booking.items || []).reduce(
		(sum, item) => sum + Number(item.duration || 0),
		0
	);
	if (!minutes) return "--";
	return `${minutes}m`;
});
</script>
