<template>
	<div class="my-4 w-full max-w-7xl mx-auto px-4">
		<div class="grid grid-cols-1 lg:grid-cols-12 lg:gap-12">
			<!-- Left Section  -->
			<div class="lg:col-span-8 flex flex-col gap-10">
				<div class="space-y-6">
					<div
						class="relative w-full aspect-[16/9] lg:aspect-[21/9] rounded-xl overflow-hidden shadow-sm group"
					>
						<img
							class="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700"
							:alt="serviceDetails.name"
							:src="serviceDetails.image"
						/>

						<div class="absolute bottom-4 left-4 z-20 flex gap-2">
							<ServiceTag v-for="tag in serviceDetails.tags" :tag="tag" :key="tag" />
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-3">
					<h2>{{ serviceDetails.name }}</h2>
					<p>{{ serviceDetails.short_description }}</p>
				</div>

				<div class="bg-white p-8 rounded-xl shadow-sm border border-slate-100">
					<p>About the Service</p>
					<div v-html="serviceDetails.description"></div>
				</div>

				<div>
					Top Specialists

					<div class="grid lg:grid-cols-2 gap-4">
						<ProviderCard
							v-for="provider in serviceDetails.providers"
							:provider="provider"
							:key="provider.provider_name"
						/>
					</div>
				</div>
			</div>
			<!-- Right section  -->
			<div class="lg:col-span-4 relative">
				<div class="flex flex-col gap-4 bg-white/80 p-8">
					<div class="flex justify-between">
						<div>
							<p>Starting from</p>
							<span
								>{{
									formatCurrency(
										serviceDetails.prices[0].rate,
										serviceDetails.prices[0].currency
									)
								}}
								/ session</span
							>
						</div>
						<FeatherIcon class="h-12" name="tag" />
					</div>
					<div>
						<h3>Duration</h3>
						<div>
							<span> {{ serviceDetails.default_duration_in_minutes }} min</span>
						</div>
					</div>
					<div>
						<p>DATE & TIME</p>
						<input type="" placeholder="Select a slot" />
					</div>

					<div>
						<Button
							class="mt-4 w-full bg-primary text-gray-900 font-semibold py-2.5 rounded-xl hover:bg-primary-dark hover:text-white transition-all duration-300"
						>
							Book Now
						</Button>
					</div>
				</div>
				<div></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useRoute } from "vue-router";
import { createResource, FeatherIcon, Button } from "frappe-ui";
import ServiceTag from "@/components/ServiceTag.vue";
import ProviderCard from "@/components/ProviderCard.vue";
import { formatCurrency } from "@/utils";
import { computed, ref } from "vue";

const route = useRoute();

const serviceTypeDetailsResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_type_details",
	makeParams() {
		return {
			service_type: route.params.name,
		};
	},
	auto: true,
});

const serviceDetails = computed(() => {
	if (serviceTypeDetailsResource.data) {
		return serviceTypeDetailsResource.data;
	}
	return {};
});
</script>
