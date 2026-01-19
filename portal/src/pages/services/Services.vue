<template>
	<div class="my-4 w-full max-w-7xl mx-auto px-4">
		<div class="mb-10 max-w-3xl">
			<h2 class="text-3xl md:text-4xl font-black text-gray-900 mb-4">Select a Service</h2>
			<p class="text-lg text-gray-500 leading-relaxed">
				Choose from our curated range of professional treatments designed for your ultimate
				relaxation and well-being
			</p>
		</div>

		<!-- Search section  -->
		<div class="flex justify-between items-center my-8">
			<div class="relative">
				<FeatherIcon class="h-5 text-gray-500 absolute top-2 left-5" name="search" />
				<input
					class="rounded-lg border-0 shadow-sm px-16"
					type="search"
					placeholder="Search for a service..."
				/>
			</div>

			<div class="flex gap-4 items-center">
				<span class="px-6 py-2 rounded-full text-white bg-primary">All</span>
				<span class="px-6 py-2 rounded-full text-gray-700 bg-white">Hair</span>
				<span class="px-6 py-2 rounded-full text-gray-700 bg-white">Spa</span>
				<span class="px-6 py-2 rounded-full text-gray-700 bg-white">Nails</span>
				<span class="px-6 py-2 rounded-full text-gray-700 bg-white">Facial</span>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
			<ServiceCard
				v-for="serviceType in serviceTypes"
				:key="serviceType.name"
				:serviceType="serviceType"
			/>
		</div>
	</div>
</template>

<script setup>
import ServiceCard from "@/components/services/ServiceCard.vue";
import { createResource, FeatherIcon } from "frappe-ui";
import { computed } from "vue";

const serviceTypesResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	method: "GET",
	auto: true,
	// cache: serviceTypesResource
});

const serviceTypes = computed(() => {
	if (serviceTypesResource.data) {
		return serviceTypesResource.data;
	}
	return [];
});
</script>
