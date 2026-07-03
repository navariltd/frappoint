<template>
	<section class="space-y-4">
		<div class="flex items-center justify-between gap-4">
			<label class="block font-label-md text-label-md text-on-surface-variant"
				>Select Duration</label
			>
			<p
				v-if="service?.min_guests || service?.max_guests"
				class="text-label-sm text-on-surface-variant/80"
			>
				{{ guestText }}
			</p>
		</div>

		<div v-if="packages.length" class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
			<ServicePackageCard
				v-for="servicePackage in packages"
				:key="servicePackage.price_name || servicePackage.name"
				:service-package="servicePackage"
				:selected="
					selectedPackageKey === (servicePackage.price_name || servicePackage.name)
				"
				@select="$emit('select', servicePackage)"
			/>
		</div>

		<p
			v-else
			class="rounded-2xl border border-dashed border-outline-variant/30 px-4 py-6 text-body-md text-on-surface-variant/70"
		>
			No packages available for this service yet.
		</p>
	</section>
</template>

<script setup>
import { computed } from "vue";
import ServicePackageCard from "@/components/service-details/ServicePackageCard.vue";

const props = defineProps({
	packages: {
		type: Array,
		default: () => [],
	},
	selectedPackage: {
		type: Object,
		default: null,
	},
	service: {
		type: Object,
		default: () => ({}),
	},
});

defineEmits(["select"]);

const selectedPackageKey = computed(
	() => props.selectedPackage?.price_name || props.selectedPackage?.name || ""
);
const guestText = computed(() => {
	if (props.service?.min_guests && props.service?.max_guests) {
		return `Guests ${props.service.min_guests} - ${props.service.max_guests}`;
	}

	if (props.service?.min_guests) {
		return `Minimum ${props.service.min_guests} guests`;
	}

	if (props.service?.max_guests) {
		return `Up to ${props.service.max_guests} guests`;
	}

	return "";
});
</script>
