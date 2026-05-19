<template>
	<div
		class="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant flex gap-4 shadow-[0px_4px_20px_rgba(45,52,54,0.05)]"
	>
		<div
			class="h-14 w-14 rounded-2xl bg-surface-container-high flex items-center justify-center text-primary font-bold text-[16px] overflow-hidden shrink-0"
		>
			{{ initials }}
		</div>
		<div class="flex-grow min-w-0">
			<div class="flex justify-between items-start gap-2">
				<h3 class="text-[16px] font-semibold text-on-surface truncate">
					{{ booking.customerName }}
				</h3>
				<span
					class="text-[10px] font-bold uppercase px-2 py-0.5 bg-tertiary-fixed text-on-tertiary-fixed rounded"
					>Customer</span
				>
			</div>
			<p class="text-on-surface-variant text-[13px] truncate mt-1">
				{{ booking.email || "No email available" }}
			</p>
			<p class="text-on-surface-variant text-[13px] mt-1">
				{{ booking.mobileNo || "No phone available" }}
			</p>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ booking: { type: Object, required: true } });

const initials = computed(() => {
	const source = props.booking.customerName || "BK";
	return source
		.split(" ")
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() || "")
		.join("");
});
</script>
