<template>
	<div class="px-6 py-5 space-y-5 max-w-6xl">
		<p class="text-[13px] text-on-surface-variant">
			Search, pick a room and rate, choose the guest, then hold. Holds are released after
			{{ hotel.holdExpiryMinutes }} minutes unless confirmed.
		</p>

		<HotelUnavailable v-if="blocked" :message="blocked" />

		<template v-else>
			<form
				class="grid grid-cols-2 md:grid-cols-5 gap-3 items-end rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				@submit.prevent="search"
			>
				<label class="text-[12px] text-on-surface-variant">
					Arrival
					<input
						v-model="arrival"
						type="date"
						:min="businessDate"
						class="hotel-input"
						required
					/>
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Departure
					<input
						v-model="departure"
						type="date"
						:min="minDeparture"
						class="hotel-input"
						required
					/>
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Adults
					<input
						v-model.number="adults"
						type="number"
						min="1"
						class="hotel-input"
						required
					/>
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Children
					<input v-model.number="children" type="number" min="0" class="hotel-input" />
				</label>
				<p class="order-last col-span-2 md:col-span-5 text-[12px] text-on-surface-variant">
					{{ nights }} night{{ nights === 1 ? "" : "s" }}
					<span v-if="businessDate">
						· Business date {{ formatNight(businessDate) }}</span
					>
				</p>
				<button
					type="submit"
					class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
					:disabled="searching || nights < 1"
				>
					{{ searching ? "Searching…" : "Search" }}
				</button>
			</form>

			<p
				v-if="error"
				class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
			>
				{{ error }}
			</p>

			<div class="grid md:grid-cols-5 gap-5">
				<section class="md:col-span-3 space-y-3">
					<p
						v-if="searched && !options.length"
						class="text-[13px] text-on-surface-variant"
					>
						Nothing is priced for these dates.
					</p>
					<article
						v-for="option in options"
						:key="`${option.room_type}|${option.rate_plan}`"
						class="rounded-xl border p-4 transition-colors"
						:class="[
							isSelected(option)
								? 'border-primary bg-primary-container/10'
								: 'border-outline-variant bg-surface-container-lowest',
							option.offered ? '' : 'opacity-60',
						]"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h2 class="text-[15px] font-semibold text-on-surface">
									{{ option.room_type_name }}
								</h2>
								<p class="text-[12px] text-on-surface-variant">
									{{ option.rate_plan_name }}
									<span v-if="option.tax_inclusive"> · tax included</span>
								</p>
							</div>
							<div class="text-right">
								<p class="text-[16px] font-semibold text-on-surface">
									{{
										option.offered
											? formatMoney(option.total, option.currency)
											: option.reasons.join(", ")
									}}
								</p>
								<p
									v-if="option.offered"
									class="text-[11px] text-on-surface-variant"
								>
									{{ formatMoney(option.average_rate, option.currency) }} average
									per night
								</p>
							</div>
						</div>
						<div class="mt-3 flex flex-wrap gap-1.5">
							<span
								v-for="night in option.nights"
								:key="night.night"
								class="rounded px-2 py-1 text-[11px]"
								:class="
									night.sellable
										? 'bg-surface-container text-on-surface'
										: 'bg-error-container text-on-error-container'
								"
								:title="night.reason || `${night.available} left`"
							>
								{{ formatNight(night.night) }} ·
								{{
									night.rate != null
										? formatMoney(night.rate, option.currency)
										: night.reason
								}}
							</span>
						</div>
						<button
							v-if="option.offered"
							type="button"
							class="mt-3 rounded-lg border border-primary px-3 py-1.5 text-[12px] font-semibold"
							:class="
								isSelected(option) ? 'bg-primary text-on-primary' : 'text-primary'
							"
							@click="selected = option"
						>
							{{ isSelected(option) ? "Selected" : "Select" }}
						</button>
					</article>
				</section>

				<aside class="md:col-span-2">
					<div
						v-if="selected"
						class="sticky top-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
					>
						<div>
							<p class="text-[12px] uppercase tracking-wide text-on-surface-variant">
								Your selection
							</p>
							<p class="text-[15px] font-semibold text-on-surface">
								{{ selected.room_type_name }} · {{ selected.rate_plan_name }}
							</p>
							<p class="text-[12px] text-on-surface-variant">
								{{ formatNight(selected.arrival) }} →
								{{ formatNight(selected.departure) }} ·
								{{ selected.adults }} adult{{ selected.adults === 1 ? "" : "s" }}
								<span v-if="selected.children"
									>, {{ selected.children }} children</span
								>
							</p>
							<p class="mt-1 text-[16px] font-semibold">
								{{ formatMoney(selected.total, selected.currency) }}
							</p>
						</div>

						<div class="space-y-1">
							<p class="text-[12px] font-semibold text-on-surface">Lead guest</p>
							<GuestPicker v-model="guest" />
						</div>

						<label class="block text-[12px] text-on-surface-variant">
							Booking source
							<select v-model="bookingSource" class="hotel-input" required>
								<option
									v-for="source in hotel.bookingSources"
									:key="source"
									:value="source"
								>
									{{ source }}
								</option>
							</select>
						</label>
						<label class="block text-[12px] text-on-surface-variant">
							Notes
							<textarea v-model="notes" rows="2" class="hotel-input" />
						</label>

						<button
							type="button"
							class="w-full rounded-lg bg-primary text-on-primary px-4 py-2.5 text-[13px] font-semibold disabled:opacity-50"
							:disabled="!guest || !bookingSource || holding"
							@click="holdRooms"
						>
							{{ holding ? "Holding…" : "Hold room" }}
						</button>
					</div>
					<p v-else class="text-[13px] text-on-surface-variant">
						Select a room and rate to continue.
					</p>
				</aside>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { holdStaysApi, hotelErrorMessage, searchAvailabilityApi } from "@/api/hotel.api";
import GuestPicker from "@/components/hotel/GuestPicker.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useHotelStore } from "@/stores/hotel.store";
import { addDays, formatMoney, formatNight, nightsBetween } from "@/utils/hotelFormat";

const hotel = useHotelStore();
const router = useRouter();

const arrival = ref("");
const departure = ref("");
const adults = ref(2);
const children = ref(0);
const options = ref([]);
const selected = ref(null);
const guest = ref(null);
const bookingSource = ref("");
const notes = ref("");
const searching = ref(false);
const searched = ref(false);
const holding = ref(false);
const error = ref("");

const propertyName = computed(() => hotel.property);
const businessDate = computed(() => hotel.currentProperty?.business_date || "");
const minDeparture = computed(() => (arrival.value ? addDays(arrival.value, 1) : ""));
const nights = computed(() => nightsBetween(arrival.value, departure.value));
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.canBook) return "You don't have a role that can take reservations.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

onMounted(async () => {
	await hotel.load();
	resetDates();
	bookingSource.value = hotel.bookingSources.includes("Walk In")
		? "Walk In"
		: hotel.bookingSources[0] || "";
});

watch(propertyName, () => {
	resetDates();
	clearResults();
});

watch(arrival, (value) => {
	if (value && (!departure.value || departure.value <= value))
		departure.value = addDays(value, 1);
});

function resetDates() {
	if (!businessDate.value) return;
	if (!arrival.value || arrival.value < businessDate.value) arrival.value = businessDate.value;
	if (!departure.value || departure.value <= arrival.value)
		departure.value = addDays(arrival.value, 1);
}

function clearResults() {
	options.value = [];
	selected.value = null;
	searched.value = false;
}

function isSelected(option) {
	return (
		selected.value?.room_type === option.room_type &&
		selected.value?.rate_plan === option.rate_plan
	);
}

async function search() {
	error.value = "";
	clearResults();
	searching.value = true;
	try {
		options.value =
			(await searchAvailabilityApi({
				property: propertyName.value,
				arrival: arrival.value,
				departure: departure.value,
				adults: adults.value,
				children: children.value,
			})) || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		searching.value = false;
		searched.value = true;
	}
}

async function holdRooms() {
	error.value = "";
	holding.value = true;
	try {
		const booking = await holdStaysApi({
			property: propertyName.value,
			stays: [
				{
					room_type: selected.value.room_type,
					rate_plan: selected.value.rate_plan,
					arrival: selected.value.arrival,
					departure: selected.value.departure,
					adults: selected.value.adults,
					children: selected.value.children,
					lead_guest: guest.value.name,
					notes: notes.value || null,
				},
			],
			bookingDetails: {
				booking_source: bookingSource.value,
				booker_guest_profile: guest.value.name,
			},
		});
		router.push({ name: "HotelBooking", params: { bookingId: booking.name } });
	} catch (e) {
		const message = hotelErrorMessage(e);
		await search(); // the room may have just sold out: show current availability
		error.value = message;
	} finally {
		holding.value = false;
	}
}
</script>

<style scoped>
.hotel-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
