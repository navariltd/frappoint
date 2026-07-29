<template>
	<section
		class="relative isolate overflow-hidden rounded-[2rem] border border-outline-variant/20 bg-primary shadow-xl shadow-primary/10"
	>
		<img
			v-if="service.image"
			:src="service.image"
			:alt="service.appointment_type"
			class="absolute inset-0 -z-20 h-full w-full object-cover"
		/>
		<div
			v-else
			class="absolute inset-0 -z-20 flex items-center justify-end bg-gradient-to-br from-primary to-primary-dark pr-12 text-on-primary/10"
		></div>
		<span
			v-if="!service.image"
			class="material-symbols-outlined absolute right-8 top-1/2 -z-10 -translate-y-1/2 text-[15rem] text-on-primary/10"
			aria-hidden="true"
			>spa</span
		>
		<div
			class="absolute inset-0 -z-10 bg-gradient-to-r from-black/80 via-black/45 to-black/15"
		></div>

		<div
			class="relative flex min-h-[28rem] flex-col justify-end gap-8 p-6 sm:p-10 lg:min-h-[34rem]"
		>
			<div class="grid items-end gap-8 lg:grid-cols-[minmax(0,1fr)_auto]">
				<div class="max-w-3xl space-y-4 text-white">
					<nav
						class="flex flex-wrap items-center gap-2 text-label-sm text-white/75"
						aria-label="Breadcrumb"
					>
						<RouterLink
							:to="{ name: 'Services' }"
							class="hover:text-white hover:underline"
						>
							Services
						</RouterLink>
						<template v-if="service.item_group">
							<span aria-hidden="true">/</span>
							<span>{{ service.item_group }}</span>
						</template>
					</nav>
					<h1 class="font-headline-lg text-headline-lg leading-tight text-white">
						{{ title }}
					</h1>
					<p
						v-if="subtitle"
						class="max-w-2xl font-body-md text-body-md leading-relaxed text-white/85"
					>
						{{ subtitle }}
					</p>

					<div v-if="tags.length" class="flex flex-wrap gap-2 pt-1">
						<span v-for="tag in tags" :key="tag" class="inline-flex">
							<ServiceTag :tag="tag" />
						</span>
					</div>
				</div>

				<div
					v-if="startingPrice"
					class="w-fit rounded-2xl border border-white/25 bg-surface-container-lowest/95 px-6 py-5 text-on-surface shadow-xl backdrop-blur"
				>
					<p
						class="text-label-sm font-semibold uppercase tracking-[0.14em] text-on-surface-variant"
					>
						Starting from
					</p>
					<p class="mt-1 font-headline-md text-headline-md font-bold text-primary">
						{{ startingPrice }}
					</p>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import ServiceTag from "@/components/common/ServiceTag.vue";
import { formatCurrency } from "@/utils";

const props = defineProps({
	service: {
		type: Object,
		default: () => ({}),
	},
});

const title = computed(
	() => props.service?.appointment_type || props.service?.name || "Service Details"
);
const subtitle = computed(() => props.service?.short_description || "");
const tags = computed(() => props.service?.tags || []);
const startingPrice = computed(() => {
	const prices = (props.service?.prices || []).filter(
		(price) => price?.amount != null && price?.currency
	);
	if (!prices.length) {
		return "";
	}

	const lowest = prices.reduce((current, price) =>
		Number(price.amount) < Number(current.amount) ? price : current
	);
	return formatCurrency(lowest.amount, lowest.currency);
});
</script>
