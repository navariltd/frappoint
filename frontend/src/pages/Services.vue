<template>
	<AppLayout>
		<main class="p-6">
			<h1 class="text-2xl font-bold mb-6">Appointment Type</h1>

			<!-- Loading State -->
			<div v-if="serviceTypes.loading" class="flex justify-center items-center py-12">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
			</div>

			<!-- Service Types Grid -->
			<div
				v-else-if="serviceTypes.data && serviceTypes.data.length > 0"
				class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
			>
				<ServiceCard
					v-for="service in serviceTypes.data"
					:key="service.name"
					:service="service"
					@book="bookService"
				/>
			</div>

			<!-- Empty State -->
			<div v-else class="text-center py-12">
				<p class="text-gray-600">No services available at the moment.</p>
			</div>
		</main>
	</AppLayout>
</template>

<script setup>
import { createResource } from "frappe-ui";
import AppLayout from "@/components/AppLayout.vue";
import ServiceCard from "@/components/ServiceCard.vue";

const serviceTypes = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	auto: true,
});

const bookService = (service) => {
	console.log("Book clicked:", service);
	// next step → router push to calendar
};
</script>
