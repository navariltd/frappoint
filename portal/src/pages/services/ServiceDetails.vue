<template>
	<div class="my-10 w-full max-w-7xl mx-auto px-4">
		<div class="grid grid-cols-1 lg:grid-cols-12 lg:gap-12">
			<!-- Left Section  -->
			<div class="lg:col-span-8 flex flex-col gap-10">
				<div class="space-y-6">
					<div
						class="relative w-full aspect-[16/9] lg:aspect-[21/9] rounded-xl overflow-hidden shadow-sm group"
						style="
							background: linear-gradient(
								to bottom right,
								#3a8a8b,
								#2c7677,
								#1f5a5b
							);
						"
					>
						<div
							class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
							:data-alt="serviceDetails.name"
							:style="{ backgroundImage: `url(${serviceDetails.image})` }"
						></div>

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
								v-if="servicePrice.amount && servicePrice.currency"
								class="text-2xl font-black"
							>
								{{ formatCurrency(servicePrice.amount, servicePrice.currency) }}
								<span class="text-lg text-gray-700">/ session</span>
							</h2>
						</div>
						<div class="bg-background-light rounded-full p-4">
							<FeatherIcon class="h-6" name="tag" color="#236061" :strokeWidth="3" />
						</div>
					</div>
					<div>
						<h3 class="font-medium text-lg mb-4">PRICES</h3>
						<div class="grid grid-cols-2 gap-2">
							<div
								v-for="price in serviceDetails.prices"
								:key="price.price_name"
								@click="setSelectedPrice(price)"
								class="px-4 py-4 rounded-lg cursor-pointer flex flex-col gap-2 border-2 transition-all"
								:class="
									booking.draft.priceName === price.price_name
										? 'border-primary bg-primary/10'
										: 'border-gray-300 hover:border-primary'
								"
							>
								<span
									class="font-bold text-sm text-gray-700 uppercase tracking-wide"
								>
									{{ price.price_name }}
								</span>
								<span class="font-semibold text-primary text-xl">
									{{ price.duration }} min
								</span>
								<span class="text-sm font-semibold text-gray-900">
									{{ formatCurrency(price.amount, price.currency) }}
								</span>
								<span class="text-xs text-gray-500" v-if="price.guest_count">
									{{ price.guest_count }}
									{{ price.guest_count === 1 ? "guest" : "guests" }}
								</span>
							</div>
						</div>
					</div>
					<!-- <div><div
							class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
							:data-alt="serviceDetails.name"
							:style="{ backgroundImage: `url(${serviceDetails.image})` }"
						></div>
						<p class="text-gray-900 font-medium mb-4">DATE & TIME</p>
						<FormControl type="text" size="lg" placeholder="Select a Slot">
							<template #suffix>
								<FeatherIcon class="w-4" name="calendar" />
							</template>
						</FormControl>
					</div> -->

					<div>
						<Button
							@click="showBookingDialog"
							class="mt-4 w-full font-semibold py-6 rounded-xl transition-all duration-300 text-lg"
							:class="
								isPriceSelected
									? '!bg-primary !text-white/80 hover:!bg-primary-dark hover:!text-white'
									: 'bg-gray-300 text-gray-500 cursor-not-allowed'
							"
						>
							Book Appointment
						</Button>
					</div>
				</div>
				<div></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { createResource, FeatherIcon, Button, FormControl } from "frappe-ui";
import ServiceTag from "@/components/common/ServiceTag.vue";
import ProviderCard from "@/components/providers/ProviderCard.vue";
import { formatCurrency } from "@/utils";
import { computed, watch } from "vue";
import { useBookingStore } from "@/stores/bookingStore";

const booking = useBookingStore();
const route = useRoute();
const router = useRouter();

const isPriceSelected = computed(() => {
	return !!booking.draft.priceName;
});

function showBookingDialog() {
	if (!isPriceSelected.value) {
		return;
	}
	router.push({
		name: "BookingDetails",
		params: { serviceType: serviceDetails.value.name },
	});
	booking.setServiceType(serviceDetails.value.name);
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
	if (booking.draft.priceName) {
		return {
			price_name: booking.draft.priceName,
			amount: booking.draft.price,
			currency: booking.draft.currency,
		};
	}
	return serviceDetails.value.prices?.[0] || {};
});

watch(
	() => serviceDetails.value.prices,
	(prices) => {
		if (prices?.length && !booking.draft.priceName) {
			const first = prices[0];
			booking.setPriceName(first.price_name);
			booking.setPrice(first.amount);
			booking.setCurrency(first.currency);
			booking.setDuration(first.duration);

			// Set number of guests from first price
			const guestCount = first.guest_count || 1;
			booking.setNumberOfGuests(guestCount);
		}
	},
	{ immediate: true }
);

const setSelectedPrice = (price) => {
	booking.setPriceName(price.price_name);
	booking.setPrice(price.amount);
	booking.setCurrency(price.currency);
	booking.setDuration(price.duration);

	// Set number of guests from price
	const guestCount = price.guest_count || 1;
	booking.setNumberOfGuests(guestCount);
};
</script>
