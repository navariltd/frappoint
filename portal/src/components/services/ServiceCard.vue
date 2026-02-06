<template>
	<div
		class="group bg-surface-light rounded-2xl overflow-hidden border border-gray-100 shadow-[0_2px_12px_rgba(0,0,0,0.04)] flex-col justify-center"
	>
		<div class="relative h-48 overflow-hidden">
			<RouterLink :to="{ name: 'ServiceDetails', params: { name: serviceType.name } }">
				<div
					class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110"
					:data-alt="serviceType.name"
					:style="{ backgroundImage: `url(${serviceType.image})` }"
				></div>
				<p
					class="absolute top-3 right-3 bg-white/90 rounded-lg text-xs font-bold text-primary px-2.5 py-1 shadow-sm"
				>
					{{ serviceType.item_group }}
				</p>
			</RouterLink>
		</div>

		<div class="p-5 flex flex-col flex-grow">
			<div class="flex justify-between items-start mb-2">
				<h3 class="text-2xl font-semibold">{{ serviceType.name }}</h3>
			</div>

			<p
				class="text-sm text-gray-500 line-clamp-2 mb-6"
				v-html="serviceType.short_description"
			></p>

			<div class="mt-auto pt-4 border-t border-gray-100 flex items-center justify-between">
				<div class="flex flex-col">
					<span class="text-xs text-gray-400 font-medium mb-2">Price</span>
					<span class="text-base font-bold text-gray-900">{{
						formatCurrency(serviceType.price.amount, serviceType.price.currency)
					}}</span>
				</div>

				<div
					class="flex items-center justify-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-md"
				>
					<FeatherIcon class="h-4" name="clock" />
					<p>{{ serviceType.default_duration_in_minutes }}m</p>
				</div>
			</div>

			<Button
				@click="showBookingDialog"
				class="mt-4 w-full bg-background-light text-gray-900 font-semibold py-5 rounded-xl hover:!bg-primary hover:!text-white transition-all duration-300"
			>
				Book Now
			</Button>
		</div>
	</div>
</template>

<script setup>
import { Button, FeatherIcon } from "frappe-ui";
import { formatCurrency } from "@/utils";
import { useBookingStore } from "@/stores/bookingStore";
import { useRouter } from "vue-router";

const props = defineProps({
	serviceType: Object,
});

const booking = useBookingStore();
const router = useRouter();

function showBookingDialog() {
	router.push({
		name: "BookingDetails",
		params: { serviceType: props.serviceType.name },
	});
	booking.setServiceType(props.serviceType.name);
	booking.setPriceName(props.serviceType?.price.price_name);
	booking.setPrice(props.serviceType.price?.amount);
	booking.setCurrency(props.serviceType.price?.currency);
}
</script>
