<template>
	<div class="px-6 py-5 max-w-[1600px]">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<div
			v-else
			class="grid gap-5 lg:grid-cols-[minmax(320px,420px)_minmax(0,1fr)] lg:items-start"
		>
			<!-- Bookings list. On small screens it gives way to the selected booking. -->
			<section
				class="space-y-3 lg:sticky lg:top-4"
				:class="{ 'hidden lg:block': selectedId }"
				aria-label="Bookings"
			>
				<div class="space-y-2">
					<label class="relative block">
						<span
							class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
							aria-hidden="true"
							>search</span
						>
						<input
							v-model="search"
							type="search"
							class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-[13px] text-on-surface"
							placeholder="Guest, booking or source"
							aria-label="Search bookings"
						/>
					</label>
					<div class="flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
						<button
							v-for="option in FILTERS"
							:key="option.key"
							type="button"
							class="rounded-full border px-3 py-1 text-[12px] font-semibold"
							:class="
								filter === option.key
									? 'border-primary bg-primary text-on-primary'
									: 'border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container'
							"
							:aria-pressed="filter === option.key"
							@click="filter = option.key"
						>
							{{ option.label }}
							<span class="ml-1 opacity-80">{{ counts[option.key] }}</span>
						</button>
					</div>
				</div>

				<p
					v-if="error"
					class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
				>
					{{ error }}
				</p>
				<p
					v-else-if="loading && !bookings.length"
					class="text-[13px] text-on-surface-variant"
				>
					Loading…
				</p>
				<p v-else-if="!bookings.length" class="text-[13px] text-on-surface-variant">
					No bookings yet.
				</p>
				<p v-else-if="!visible.length" class="text-[13px] text-on-surface-variant">
					No bookings match.
				</p>

				<ul
					v-else
					class="divide-y divide-outline-variant overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest lg:max-h-[calc(100vh-15rem)] lg:overflow-y-auto"
				>
					<li v-for="row in visible" :key="row.name">
						<RouterLink
							:to="{ name: 'HotelBooking', params: { bookingId: row.name } }"
							class="block border-l-[3px] px-4 py-3 transition-colors"
							:class="
								row.name === selectedId
									? 'border-l-primary bg-primary/5'
									: 'border-l-transparent hover:bg-surface-container'
							"
							:aria-current="row.name === selectedId ? 'page' : undefined"
						>
							<span class="flex items-start justify-between gap-3">
								<span class="min-w-0">
									<span
										class="block truncate text-[14px] font-semibold text-on-surface"
										>{{
											row.lead_guest_name || row.booker_name || row.name
										}}</span
									>
									<span class="block text-[12px] text-on-surface-variant">
										<template v-if="row.arrival_date">
											{{ formatNight(row.arrival_date) }} →
											{{ formatNight(row.departure_date) }} ·
										</template>
										{{ row.room_count }} room{{
											row.room_count === 1 ? "" : "s"
										}}
									</span>
								</span>
								<HotelStatusBadge :status="row.status" />
							</span>
							<span
								class="mt-1 flex items-center justify-between gap-3 text-[12px] text-on-surface-variant"
							>
								<span class="truncate"
									>{{ row.name }} · {{ row.booking_source }}</span
								>
								<span class="shrink-0 font-semibold text-on-surface">{{
									formatMoney(row.total_amount, row.currency)
								}}</span>
							</span>
						</RouterLink>
					</li>
				</ul>
			</section>

			<!-- The selected booking -->
			<section v-if="selectedId" class="min-w-0 space-y-3" aria-label="Selected booking">
				<RouterLink
					:to="{ name: 'HotelBookings' }"
					class="text-[12px] font-semibold text-primary lg:hidden"
				>
					← All bookings
				</RouterLink>
				<div
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-5"
				>
					<BookingDetail :booking-id="selectedId" @changed="updateRow" />
				</div>
			</section>
			<section
				v-else
				class="hidden min-h-[320px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-outline-variant text-center lg:flex"
			>
				<span
					class="material-symbols-outlined text-[36px] text-on-surface-variant"
					aria-hidden="true"
					>book_online</span
				>
				<p class="text-[14px] font-semibold text-on-surface">Select a booking</p>
				<p class="max-w-xs text-[12px] text-on-surface-variant">
					Its stays, deposits and actions open here, next to the list.
				</p>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { fetchRecentBookingsApi, hotelErrorMessage } from "@/api/hotel.api";
import BookingDetail from "@/components/hotel/BookingDetail.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useHotelStore } from "@/stores/hotel.store";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

const FILTERS = [
	{ key: "all", label: "All", statuses: null },
	{ key: "open", label: "Open", statuses: ["Option", "Confirmed", "Partly Cancelled"] },
	{ key: "closed", label: "Closed", statuses: ["Closed"] },
	{ key: "cancelled", label: "Cancelled", statuses: ["Cancelled"] },
];
const BOOKINGS_SHOWN = 100;

const route = useRoute();
const hotel = useHotelStore();
const bookings = ref([]);
const loading = ref(false);
const error = ref("");
const search = ref("");
const filter = ref("all");

const propertyName = computed(() => hotel.property);
const selectedId = computed(() => route.params.bookingId || null);
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

const matching = computed(() => {
	const text = search.value.trim().toLowerCase();
	if (!text) return bookings.value;
	return bookings.value.filter((row) =>
		[row.name, row.lead_guest_name, row.booker_name, row.booking_source]
			.filter(Boolean)
			.some((value) => value.toLowerCase().includes(text))
	);
});
const counts = computed(() =>
	Object.fromEntries(
		FILTERS.map((option) => [
			option.key,
			option.statuses
				? matching.value.filter((row) => option.statuses.includes(row.status)).length
				: matching.value.length,
		])
	)
);
const visible = computed(() => {
	const statuses = FILTERS.find((option) => option.key === filter.value)?.statuses;
	return statuses
		? matching.value.filter((row) => statuses.includes(row.status))
		: matching.value;
});

async function load() {
	if (!propertyName.value) return;
	loading.value = true;
	error.value = "";
	try {
		bookings.value = (await fetchRecentBookingsApi(propertyName.value, BOOKINGS_SHOWN)) || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

/** A command on the selected booking changed it: show its new status and total in the list. */
function updateRow(summary) {
	const row = bookings.value.find((item) => item.name === summary?.name);
	if (!row) return load();
	Object.assign(row, {
		status: summary.status,
		total_amount: summary.total_amount,
		stay_count: summary.stay_count,
	});
}

onMounted(async () => {
	await hotel.load();
	load();
});
watch(propertyName, load);
</script>
