<template>
	<div class="my-10 w-full max-w-7xl mx-auto px-4">
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
					<h2 class="text-3xl font-black">{{ serviceDetails.name }}</h2>
					<p class="text-m text-gray-700">{{ serviceDetails.short_description }}</p>
				</div>

				<div class="bg-white p-8 rounded-xl shadow-lg border border-slate-100">
					<div class="flex gap-2 items-center mb-6">
						<FeatherIcon class="h-6" name="file-text" color="#2c7677" />
						<p class="text-lg font-semibold">About the Service</p>
					</div>

					<div class="text-xl/6 text-gray-700" v-html="serviceDetails.description"></div>
				</div>

				<div>
					<h3 class="mb-6 font-semibold text-2xl">Top Specialists</h3>

					<div class="grid lg:grid-cols-2 gap-4 mb-4">
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
				<div
					class="flex flex-col gap-4 bg-white/80 p-8 rounded-lg shadow-lg border-gray-300"
				>
					<div class="flex justify-between mb-4">
						<div>
							<p class="text-gray-700 mb-2">Starting from</p>
							<h2
								v-if="servicePrice.rate && servicePrice.currency"
								class="text-2xl font-black"
							>
								{{ formatCurrency(servicePrice.rate, servicePrice.currency) }}
								<span class="text-lg text-gray-700">/ session</span>
							</h2>
						</div>
						<div class="bg-background-light rounded-full p-4">
							<FeatherIcon class="h-6" name="tag" color="#236061" :strokeWidth="3" />
						</div>
					</div>
					<div>
						<h3 class="font-medium text-lg mb-4">DURATION</h3>
						<div
							class="border-primary border-2 px-6 py-4 rounded-lg text-center max-w-40"
						>
							<span class="font-semibold text-primary text-xl">
								{{ serviceDetails.default_duration_in_minutes }} min</span
							>
						</div>
					</div>
					<div>
						<p class="text-gray-900 font-medium mb-4">DATE & TIME</p>
						<FormControl type="text" size="lg" placeholder="Select a Slot">
							<template #suffix>
								<FeatherIcon class="w-4" name="calendar" />
							</template>
						</FormControl>
					</div>

					<div>
						<Button
							@click="showBookingDialog"
							class="mt-4 w-full !bg-primary !text-white/80 font-semibold py-6 rounded-xl hover:!bg-primary-dark hover:!text-white transition-all duration-300 text-lg"
						>
							Book Appointment
						</Button>

						<BookingDialog v-model="openBooking" @close="showBookingDialog = false" />
					</div>
				</div>
				<div></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useRoute } from "vue-router";
import { createResource, FeatherIcon, Button, FormControl } from "frappe-ui";
import ServiceTag from "@/components/common/ServiceTag.vue";
import ProviderCard from "@/components/providers/ProviderCard.vue";
import { formatCurrency } from "@/utils";
import { computed, ref, watch } from "vue";
import BookingDialog from "@/components/booking/BookingDialog.vue";
import { useBookingStore } from "@/stores/bookingStore";

const route = useRoute();
const openBooking = ref(false);
const booking = useBookingStore();

function showBookingDialog() {
	openBooking.value = true;
	booking.setServiceType(serviceDetails.value.name);
	booking.setPriceName(servicePrice.value.price_name);
	booking.setPrice(servicePrice.value.rate);
	booking.setCurrency(servicePrice.value.currency);
}

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

const servicePrice = computed(() => {
	if (serviceDetails.value.prices) {
		return serviceDetails.value.prices[0];
	}
	return {};
});
</script>
