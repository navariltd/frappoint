<template>
	<AppLayout>
		<main class="p-6">
			<h1 class="text-2xl font-bold mb-6">Appointment Type</h1>

			<!-- Loading State -->
			<div
				v-if="serviceTypes.loading"
				class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
			>
				<ServiceCardSkeleton v-for="i in 6" :key="i" />
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

		<!-- Booking Modal -->
		<BookingModal
			:isVisible="showBookingModal"
			:service="selectedService"
			@close="closeBookingModal"
			@success="handleBookingSuccess"
		/>
	</AppLayout>
</template>

<script setup>
import { ref } from "vue";
import { createResource } from "frappe-ui";
import AppLayout from "@/components/AppLayout.vue";
import ServiceCard from "@/components/ServiceCard.vue";
import ServiceCardSkeleton from "@/components/ServiceCardSkeleton.vue";
import BookingModal from "@/components/BookingModal.vue";

const serviceTypes = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	auto: true,
});

const showBookingModal = ref(false);
const selectedService = ref(null);

const bookService = (service) => {
	console.log("Book clicked:", service);
	selectedService.value = service;
	showBookingModal.value = true;
};

const closeBookingModal = () => {
	showBookingModal.value = false;
	selectedService.value = null;
};

const handleBookingSuccess = () => {
	console.log("Booking successful!");
	// TODO: Show success message, redirect to appointments page, etc.
	alert("Appointment booked successfully!");
};
</script>
