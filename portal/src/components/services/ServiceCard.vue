<template>
	<div
		class="bg-surface-container-lowest rounded-xl luxury-shadow luxury-shadow-hover transition-all flex flex-col border border-outline-variant/20 overflow-hidden group"
	>
		<div class="aspect-[16/9] overflow-hidden bg-surface-container-low">
			<img
				v-if="service.image"
				:alt="service.appointment_type"
				class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
				:src="service.image"
			/>
			<div
				v-else
				class="w-full h-full bg-primary-container flex items-center justify-center"
			>
				<span class="text-on-primary-container font-label-md text-label-md">No Image</span>
			</div>
		</div>
		<div class="p-stack-md flex flex-col flex-grow">
			<div class="flex justify-between items-start mb-2 gap-3">
				<h4 class="font-headline-sm text-headline-sm text-on-surface">
					{{ service.appointment_type }}
				</h4>
				<span class="font-label-md text-label-md text-primary whitespace-nowrap">
					{{ priceLabel }}
				</span>
			</div>
			<p
				class="font-body-md text-body-md text-on-surface-variant mb-4 h-[72px] overflow-hidden w-full"
			>
				{{ shortDescription }}
			</p>
			<div
				class="mb-5 flex items-center justify-between text-[12px] text-on-surface-variant"
			>
				<span>{{ durationLabel }}</span>
				<span v-if="service.item_group" class="truncate max-w-[50%] text-right">{{
					service.item_group
				}}</span>
			</div>
			<div class="grid grid-cols-2 gap-2">
				<button
					type="button"
					class="w-full bg-surface-container-low border border-outline-variant/30 text-on-surface py-2.5 rounded-full font-label-md text-label-md hover:bg-surface-container-high transition-all"
					@click="$emit('view', service)"
				>
					View
				</button>
				<button
					type="button"
					class="w-full bg-primary text-on-primary py-2.5 rounded-full font-label-md text-label-md hover:opacity-90 active:scale-[0.98] transition-all"
					@click="$emit('add', service)"
				>
					Add
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatCurrency } from "@/utils";

const props = defineProps({
	service: { type: Object, required: true },
});

defineEmits(["view", "add"]);

const priceLabel = computed(() => {
	if (!props.service?.price?.amount || !props.service?.price?.currency) {
		return "Price on request";
	}
	return formatCurrency(props.service.price.amount, props.service.price.currency);
});

const durationLabel = computed(() => {
	const value = Number(props.service?.default_duration_in_minutes || 0);
	if (!value) {
		return "Duration flexible";
	}
	return `${value} min`;
});

const shortDescription = computed(() => {
	const raw = String(props.service?.short_description || "").trim();
	if (!raw) {
		return "";
	}
	if (raw.length <= 140) {
		return raw;
	}
	return `${raw.slice(0, 140).trimEnd()}...`;
});
</script>
