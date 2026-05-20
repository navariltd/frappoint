<template>
	<button
		type="button"
		class="group flex w-full flex-col gap-2.5 rounded-xl border px-3.5 py-2.5 text-left transition-all duration-200"
		:class="
			selected
				? 'border-primary bg-primary/8 text-primary shadow-[0px_8px_18px_rgba(45,118,119,0.10)]'
				: 'border-outline-variant/25 bg-surface-container-lowest text-on-surface-variant hover:border-primary/45 hover:shadow-[0px_6px_14px_rgba(45,52,54,0.05)]'
		"
		:aria-pressed="selected"
		@click="$emit('select', servicePackage)"
	>
		<div class="flex items-start justify-between gap-2">
			<div class="min-w-0">
				<p
					class="truncate text-[11px] font-semibold uppercase tracking-[0.16em] text-inherit/85"
				>
					{{ servicePackage.price_name || servicePackage.name }}
				</p>
				<p class="mt-0.5 text-[12px] font-medium text-inherit/72">
					{{ servicePackage.duration }} min
				</p>
			</div>
			<p
				class="shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
				:class="
					selected
						? 'bg-primary text-white'
						: 'bg-surface-container-high text-on-surface'
				"
			>
				{{ formattedPrice }}
			</p>
		</div>

		<div class="flex items-center gap-2 text-[11px] text-on-surface-variant/75">
			<span v-if="servicePackage.pricing_model">{{ servicePackage.pricing_model }}</span>
			<span
				v-if="servicePackage.pricing_model && servicePackage.guest_count"
				class="h-1 w-1 rounded-full bg-current/35"
			></span>
			<span v-if="servicePackage.guest_count">
				{{ servicePackage.guest_count }}
				{{ servicePackage.guest_count === 1 ? "guest" : "guests" }}
			</span>
		</div>
		<div v-if="selected" class="mt-0.5 h-1 w-10 rounded-full bg-primary"></div>
	</button>
</template>

<script setup>
import { computed } from "vue";
import { formatCurrency } from "@/utils";

const props = defineProps({
	servicePackage: {
		type: Object,
		required: true,
	},
	selected: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["select"]);

const formattedPrice = computed(() =>
	formatCurrency(props.servicePackage.amount, props.servicePackage.currency)
);
</script>
