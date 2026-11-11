<template>
	<div class="px-6 py-5 space-y-5 max-w-5xl">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<p v-else-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
			{{ error }}
		</p>
		<p v-else-if="loading" class="text-[13px] text-on-surface-variant">Loading…</p>
		<p v-else-if="!bookings.length" class="text-[13px] text-on-surface-variant">
			No bookings yet.
		</p>

		<ul
			v-else
			class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
		>
			<li v-for="row in bookings" :key="row.name">
				<RouterLink
					:to="{ name: 'HotelBooking', params: { bookingId: row.name } }"
					class="flex items-center justify-between gap-3 px-4 py-3 hover:bg-surface-container"
				>
					<span>
						<span class="text-[13px] font-semibold text-on-surface">{{
							row.name
						}}</span>
						<span class="block text-[12px] text-on-surface-variant">
							{{ row.booker_name || "No booker" }} · {{ row.booking_source }} ·
							{{ row.stay_count }} active stay{{ row.stay_count === 1 ? "" : "s" }}
						</span>
					</span>
					<span class="flex items-center gap-3">
						<span class="text-[13px] font-semibold">{{
							formatMoney(row.total_amount, row.currency)
						}}</span>
						<HotelStatusBadge :status="row.status" />
					</span>
				</RouterLink>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { fetchRecentBookingsApi, hotelErrorMessage } from "@/api/hotel.api";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useHotelStore } from "@/stores/hotel.store";
import { formatMoney } from "@/utils/hotelFormat";

const hotel = useHotelStore();
const bookings = ref([]);
const loading = ref(false);
const error = ref("");

const propertyName = computed(() => hotel.property);
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

async function load() {
	if (!propertyName.value) return;
	loading.value = true;
	error.value = "";
	try {
		bookings.value = (await fetchRecentBookingsApi(propertyName.value)) || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

onMounted(async () => {
	await hotel.load();
	load();
});
watch(propertyName, load);
</script>
