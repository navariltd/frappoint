<template>
	<aside class="w-full lg:w-64 flex-shrink-0 space-y-8">
		<div>
			<h3 class="font-headline-sm text-headline-sm text-on-surface mb-4">Categories</h3>
			<div class="flex flex-col gap-2">
				<label class="flex items-center gap-3 cursor-pointer group">
					<input
						:checked="filters.categories.length === 0"
						class="rounded-sm border-outline text-primary focus:ring-primary h-5 w-5"
						type="checkbox"
						@change="$emit('clearCategories')"
					/>
					<span
						class="font-body-md text-body-md text-on-surface group-hover:text-primary transition-colors"
					>
						All Services
					</span>
				</label>
				<label
					v-for="category in categories"
					:key="category"
					class="flex items-center gap-3 cursor-pointer group"
				>
					<input
						:checked="filters.categories.includes(category)"
						class="rounded-sm border-outline text-primary focus:ring-primary h-5 w-5"
						type="checkbox"
						@change="$emit('toggleCategory', category)"
					/>
					<span
						class="font-body-md text-body-md text-on-surface-variant group-hover:text-primary transition-colors"
					>
						{{ category }}
					</span>
				</label>
			</div>
		</div>

		<div>
			<h3 class="font-headline-sm text-headline-sm text-on-surface mb-4">Duration</h3>
			<div class="flex flex-wrap gap-2">
				<button
					v-for="duration in durations"
					:key="duration"
					type="button"
					class="px-4 py-2 rounded-full border font-label-md text-label-md transition-colors"
					:class="
						filters.duration === duration
							? 'bg-secondary-container text-on-secondary-container border-secondary-container'
							: 'bg-surface-container-low border-outline-variant text-on-surface-variant hover:bg-surface-container-high'
					"
					@click="$emit('duration', duration)"
				>
					{{ duration }} min
				</button>
			</div>
		</div>

		<div>
			<h3 class="font-headline-sm text-headline-sm text-on-surface mb-4">Price Range</h3>
			<input
				type="range"
				:min="priceBounds.min"
				:max="priceBounds.max"
				step="10"
				:value="filters.maxPrice"
				class="w-full accent-primary"
				@input="$emit('price', $event.target.value)"
			/>
			<div
				class="flex justify-between mt-2 font-label-sm text-label-sm text-on-surface-variant"
			>
				<span>{{ currencySymbol }}{{ priceBounds.min }}</span>
				<span>{{ currencySymbol }}{{ filters.maxPrice }}</span>
			</div>
		</div>

		<button
			type="button"
			class="w-full bg-surface-container-low border border-outline-variant text-on-surface py-2 rounded-lg hover:bg-surface-container-high transition-colors"
			@click="$emit('clear')"
		>
			Clear Filters
		</button>
	</aside>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	filters: { type: Object, required: true },
	categories: { type: Array, default: () => [] },
	priceBounds: { type: Object, required: true },
	durations: { type: Array, default: () => [30, 60, 90, 120] },
});

defineEmits(["toggleCategory", "clearCategories", "duration", "price", "clear"]);

const currencySymbol = computed(() => {
	if (props.priceBounds.currency === "KES") return "KSh ";
	if (props.priceBounds.currency === "EUR") return "€";
	if (props.priceBounds.currency === "GBP") return "£";
	return "$";
});
</script>
