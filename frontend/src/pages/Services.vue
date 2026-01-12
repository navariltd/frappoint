<template>
	<AppLayout>
		<main class="p-6">
			<div class="flex items-center justify-between mb-6">
				<h1 class="text-2xl font-bold">Appointment Type</h1>
				<span v-if="serviceResource.loading" class="text-sm text-gray-500">
					Updating...
				</span>
			</div>

			<div v-if="serviceResource.error" class="text-red-500 p-4 bg-red-50 rounded-lg">
				{{ serviceResource.error }}
			</div>

			<div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-8">
				<ServiceCard
					v-for="service in services"
					:key="service.name"
					:service="service"
					@book="bookService"
				/>
			</div>

			<div
				v-if="!serviceResource.loading && !services.length"
				class="text-center py-20 text-gray-500"
			>
				No services available.
			</div>
		</main>
	</AppLayout>
</template>

<script setup>
import { computed } from "vue";
import { createResource } from "frappe-ui";
import { useRouter } from "vue-router";

import AppLayout from "@/components/AppLayout.vue";
import ServiceCard from "@/components/ServiceCard.vue";

const router = useRouter();

const serviceResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	auto: true,
});

const services = computed(() => {
	return serviceResource.data || [];
});

const bookService = (service) => {
	router.push({
		path: "/booking",
		query: {
			service: service.name,
		},
	});
};
</script>
