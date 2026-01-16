<template>
	<div class="my-4 w-full max-w-7xl mx-auto px-4">
		<div class="flex flex-col gap-4">
			<h1>Select a Service</h1>
			<p>
				Choose from our curated range of professional treatments designed for your ultimate
				relaxation and well-being
			</p>
		</div>

		<!-- Search section  -->
		<div class="flex justify-between items-center my-8">
			<input type="search" placeholder="Search for a service" />

			<div class="flex gap-4 items-center">
				<span>All</span>
				<span>Hair</span>
				<span>Spa</span>
				<span>Nails</span>
				<span>Facial</span>
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
import ServiceCard from "@/components/ServiceCard.vue";
import { createResource } from "frappe-ui";
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
