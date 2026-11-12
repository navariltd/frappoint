<template>
	<div class="px-6 py-5 space-y-5 max-w-5xl">
		<RouterLink :to="{ name: 'HotelBookings' }" class="text-[12px] font-semibold text-primary">
			← Bookings
		</RouterLink>

		<p v-if="loading && !booking" class="text-[13px] text-on-surface-variant">Loading…</p>
		<p
			v-if="error"
			class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
		>
			{{ error }}
		</p>

		<template v-if="booking">
			<header class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<div class="flex items-center gap-3">
						<h1 class="text-[22px] font-semibold text-on-surface">
							{{ booking.name }}
						</h1>
						<HotelStatusBadge :status="booking.status" />
					</div>
					<p class="text-[13px] text-on-surface-variant">
						{{ booking.booker_name || "No booker" }} · {{ booking.booking_source }}
						<span v-if="booking.external_reference">
							· Ref {{ booking.external_reference }}</span
						>
					</p>
				</div>
				<div class="text-right">
					<p class="text-[12px] text-on-surface-variant">Total for active stays</p>
					<p class="text-[20px] font-semibold text-on-surface">
						{{ formatMoney(booking.total_amount, booking.currency) }}
					</p>
				</div>
			</header>

			<div class="flex flex-wrap gap-2">
				<button
					v-if="heldStays.length"
					type="button"
					class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
					:disabled="busy"
					@click="run(() => confirmBookingApi(booking.name))"
				>
					Confirm
					{{ heldStays.length > 1 ? `all ${heldStays.length} stays` : "booking" }}
				</button>
				<RouterLink
					:to="{ name: 'NewReservation' }"
					class="rounded-lg border border-outline-variant px-4 py-2 text-[13px] font-semibold text-on-surface"
				>
					New reservation
				</RouterLink>
				<a
					:href="`/app/hotel-booking/${encodeURIComponent(booking.name)}`"
					target="_blank"
					class="px-4 py-2 text-[13px] text-on-surface-variant"
					>Open in desk</a
				>
			</div>

			<section class="space-y-3">
				<article
					v-for="stay in booking.stays"
					:key="stay.name"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<div class="flex items-center gap-2">
								<h2 class="text-[15px] font-semibold text-on-surface">
									{{ stay.room_type_name }} · {{ stay.rate_plan_name }}
								</h2>
								<HotelStatusBadge :status="stay.status" />
								<RouterLink
									:to="{ name: 'HotelStay', params: { stayId: stay.name } }"
									class="text-[12px] font-semibold text-primary"
									>Open stay</RouterLink
								>
							</div>
							<p class="text-[12px] text-on-surface-variant">
								{{ stay.name }} · {{ stay.lead_guest_name }} ·
								{{ formatNight(stay.arrival_date) }} →
								{{ formatNight(stay.departure_date) }} ({{ stay.nights }} night{{
									stay.nights === 1 ? "" : "s"
								}}) · {{ stay.adults }} adult{{ stay.adults === 1 ? "" : "s"
								}}<span v-if="stay.children">, {{ stay.children }} children</span>
							</p>
						</div>
						<div class="text-right">
							<p class="text-[15px] font-semibold">
								{{ formatMoney(stay.total_amount, stay.currency) }}
							</p>
							<p class="text-[11px] text-on-surface-variant">
								{{ formatMoney(stay.average_rate, stay.currency) }} average per
								night
							</p>
						</div>
					</div>

					<p
						v-if="stay.status === 'Held'"
						class="mt-3 text-[12px] font-semibold"
						:class="countdown(stay) ? 'text-on-tertiary-container' : 'text-error'"
					>
						<span class="material-symbols-outlined align-middle text-[16px]"
							>timer</span
						>
						{{
							countdown(stay)
								? `Held for ${countdown(stay)} more. Confirm before it runs out.`
								: "The hold has run out; the room is being released."
						}}
					</p>

					<div class="mt-3 flex gap-2">
						<button
							v-if="stay.can_confirm && countdown(stay)"
							type="button"
							class="rounded-lg bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="run(() => confirmStayApi(stay.name))"
						>
							Confirm
						</button>
						<button
							v-if="stay.can_cancel"
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold text-on-surface disabled:opacity-50"
							:disabled="busy"
							@click="cancelStay(stay)"
						>
							Cancel stay
						</button>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
	cancelStayApi,
	confirmBookingApi,
	confirmStayApi,
	fetchBookingApi,
	hotelErrorMessage,
} from "@/api/hotel.api";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import { formatMoney, formatNight, holdTimeLeft } from "@/utils/hotelFormat";

const route = useRoute();
const booking = ref(null);
const fetchedAt = ref(Date.now());
const now = ref(Date.now());
const loading = ref(false);
const busy = ref(false);
const error = ref("");
let ticker = null;

const heldStays = computed(
	() => booking.value?.stays.filter((stay) => stay.can_confirm && countdown(stay)) || []
);

function countdown(stay) {
	return holdTimeLeft(stay.hold_seconds_left, fetchedAt.value, now.value);
}

function show(summary) {
	booking.value = summary;
	fetchedAt.value = Date.now();
	now.value = fetchedAt.value;
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		show(await fetchBookingApi(route.params.bookingId));
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		show(await command());
	} catch (e) {
		const message = hotelErrorMessage(e);
		// Reload first: loading clears the error, and the message must stay on screen.
		await load();
		error.value = message;
	} finally {
		busy.value = false;
	}
}

function cancelStay(stay) {
	const reason = window.prompt(`Why is stay ${stay.name} being cancelled?`);
	if (reason && reason.trim()) run(() => cancelStayApi(stay.name, reason.trim()));
}

onMounted(() => {
	load();
	ticker = window.setInterval(() => (now.value = Date.now()), 1000);
});
onBeforeUnmount(() => window.clearInterval(ticker));
watch(() => route.params.bookingId, load);
</script>
