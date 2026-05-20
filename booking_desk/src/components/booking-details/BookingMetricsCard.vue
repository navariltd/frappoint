<template>
	<section
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm"
	>
		<div class="space-y-4">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline mb-2">
					Booking Metrics
				</p>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p class="text-[10px] uppercase tracking-[0.08em] text-outline font-semibold">
						Total Value
					</p>
					<p class="mt-2 text-lg font-semibold text-primary">
						{{ currency }} {{ Number(booking.grandTotal || 0).toFixed(2) }}
					</p>
				</div>
				<div class="rounded-md border border-outline-variant/30 px-3 py-2.5">
					<p class="text-[10px] uppercase tracking-[0.08em] text-outline font-semibold">
						Duration
					</p>
					<p class="mt-2 text-lg font-semibold text-on-surface">
						{{ durationLabel }}
					</p>
				</div>
			</div>
		</div>
	</section>
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
