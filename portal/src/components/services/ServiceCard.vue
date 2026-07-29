<template>
	<article
		class="flex flex-col overflow-hidden rounded-xl border border-outline-variant/20 bg-surface-container-lowest luxury-shadow transition-all hover:-translate-y-1 hover:border-primary/30 luxury-shadow-hover"
	>
		<button
			type="button"
			class="group flex flex-grow flex-col text-left focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-secondary/50 focus-visible:ring-inset"
			:aria-label="`View details for ${service.appointment_type}`"
			@click="$emit('view', service)"
		>
			<div class="aspect-[16/9] overflow-hidden bg-primary-container">
				<img
					v-if="service.image"
					:alt="service.appointment_type"
					class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
					:src="service.image"
				/>
				<div
					v-else
					class="flex h-full w-full items-center justify-center text-on-primary-container"
				>
					<span class="material-symbols-outlined text-4xl" aria-hidden="true">spa</span>
					<span class="sr-only">No image available</span>
				</div>
			</div>
			<div class="flex flex-grow flex-col p-stack-md">
				<div class="mb-2 flex items-start justify-between gap-3">
					<h2 class="font-headline-sm text-headline-sm text-on-surface">
						{{ service.appointment_type }}
					</h2>
					<span class="whitespace-nowrap font-label-md text-label-md text-primary">
						{{ priceLabel }}
					</span>
				</div>
				<p
					class="mb-4 h-[72px] w-full overflow-hidden font-body-md text-body-md text-on-surface-variant"
				>
					{{ shortDescription }}
				</p>
				<div
					class="mt-auto flex items-center justify-between text-[12px] text-on-surface-variant"
				>
					<span>{{ durationLabel }}</span>
					<span v-if="service.item_group" class="max-w-[50%] truncate text-right">
						{{ service.item_group }}
					</span>
				</div>
			</div>
		</button>

		<div class="px-stack-md pb-stack-md">
			<button
				v-if="service.price"
				type="button"
				class="inline-flex w-full items-center justify-center rounded-full bg-primary px-4 py-3 font-label-md text-label-md text-on-primary transition-all hover:bg-primary-dark active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-surface-container-high disabled:text-on-surface-variant"
				@click="$emit('add', service)"
			>
				Add to Booking
			</button>
			<button
				v-else
				type="button"
				class="inline-flex w-full items-center justify-center rounded-full border border-primary px-4 py-3 font-label-md text-label-md text-primary transition-all hover:bg-primary-container"
				@click="$emit('view', service)"
			>
				View Details
			</button>
		</div>
	</article>
</template>

<script setup>
import { computed } from "vue";
import { formatCurrency } from "@/utils";

const props = defineProps({
	service: { type: Object, required: true },
});

defineEmits(["view", "add"]);

const priceLabel = computed(() => {
	if (props.service?.price?.amount == null || !props.service?.price?.currency) {
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
