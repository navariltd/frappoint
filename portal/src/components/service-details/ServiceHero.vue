<template>
	<section
		class="relative overflow-hidden rounded-[2rem] border border-outline-variant/20 bg-surface-container-lowest shadow-[0px_18px_42px_rgba(45,52,54,0.12)]"
	>
		<div
			class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,97,97,0.28),transparent_42%),linear-gradient(135deg,rgba(7,22,22,0.94),rgba(13,54,54,0.86))]"
		></div>
		<div
			class="absolute inset-0 bg-cover bg-center opacity-35 mix-blend-screen transition-transform duration-700"
			:style="heroStyle"
		></div>
		<div
			class="absolute inset-0 bg-gradient-to-r from-black/60 via-black/25 to-transparent"
		></div>

		<div
			class="relative flex min-h-[32rem] flex-col justify-between gap-8 p-8 lg:min-h-[42rem] lg:p-10"
		>
			<div class="max-w-3xl space-y-4 text-white">
				<p class="font-label-md text-label-md uppercase tracking-[0.24em] text-white/70">
					Service Details
				</p>
				<h1 class="font-headline-lg text-headline-lg leading-tight text-white">
					{{ title }}
				</h1>
				<p class="max-w-2xl font-body-md text-body-md leading-relaxed text-white/80">
					{{ subtitle }}
				</p>
			</div>

			<div class="flex flex-wrap gap-2">
				<span v-for="tag in tags" :key="tag" class="inline-flex">
					<ServiceTag :tag="tag" />
				</span>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import ServiceTag from "@/components/common/ServiceTag.vue";

const props = defineProps({
	service: {
		type: Object,
		default: () => ({}),
	},
	selectedPackage: {
		type: Object,
		default: null,
	},
});

const title = computed(
	() => props.service?.appointment_type || props.service?.name || "Service Details"
);
const subtitle = computed(
	() =>
		props.service?.short_description ||
		"Discover the ritual, choose a package, and continue to booking."
);
const tags = computed(() => props.service?.tags || []);
const heroStyle = computed(() => {
	if (!props.service?.image) {
		return {
			backgroundImage: "linear-gradient(135deg, rgba(45,118,119,0.3), rgba(10,35,35,0.1))",
		};
	}

	return {
		backgroundImage: `url(${props.service.image})`,
	};
});
</script>
