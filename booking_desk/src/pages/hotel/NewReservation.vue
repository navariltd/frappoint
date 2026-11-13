<template>
	<div class="px-6 py-5 space-y-5 max-w-[1600px]">
		<HotelUnavailable v-if="blocked" :message="blocked" />

		<div v-else class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px] xl:items-start">
			<!-- Search and results -->
			<div class="min-w-0 space-y-4">
				<form
					class="grid grid-cols-2 md:grid-cols-[repeat(4,minmax(0,1fr))_auto] gap-3 items-end rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
					@submit.prevent="search({ force: true })"
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
						<input
							v-model.number="children"
							type="number"
							min="0"
							class="hotel-input"
						/>
					</label>
					<button
						type="submit"
						class="col-span-2 md:col-span-1 rounded-lg bg-primary text-on-primary px-6 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="searching || nights < 1"
					>
						{{ searching ? "Searching…" : "Refresh" }}
					</button>
					<div
						v-if="children > 0"
						class="col-span-2 md:col-span-5 flex flex-wrap items-end gap-2 text-[12px] text-on-surface-variant"
					>
						<span class="w-full"
							>Ages on arrival (they set each child's price band)</span
						>
						<label v-for="(_, index) in childAges" :key="index" class="w-20">
							Child {{ index + 1 }}
							<input
								v-model.number="childAges[index]"
								type="number"
								min="0"
								max="17"
								placeholder="Age"
								class="hotel-input"
							/>
						</label>
					</div>
					<p class="col-span-2 md:col-span-5 text-[12px] text-on-surface-variant">
						{{ nights }} night{{ nights === 1 ? "" : "s" }}
						<span v-if="businessDate">
							· Business date {{ formatNight(businessDate) }}</span
						>
						· Holds are released after {{ hotel.holdExpiryMinutes }} minutes unless
						confirmed.
					</p>
				</form>

				<p
					v-if="error"
					class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
				>
					{{ error }}
				</p>

				<!-- Filters -->
				<div v-if="options.length" class="flex flex-wrap items-center gap-3">
					<label class="relative min-w-[220px] flex-1">
						<span
							class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
							aria-hidden="true"
							>search</span
						>
						<input
							v-model="roomQuery"
							type="search"
							class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-[13px] text-on-surface"
							placeholder="Search room types"
							aria-label="Search room types"
						/>
					</label>
					<select
						v-model="planFilter"
						class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
						aria-label="Rate plan"
					>
						<option value="">All rate plans</option>
						<option v-for="plan in ratePlans" :key="plan.name" :value="plan.name">
							{{ plan.label }}
						</option>
					</select>
					<select
						v-model="sortBy"
						class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
						aria-label="Sort"
					>
						<option value="price">Lowest price first</option>
						<option value="name">Room type A–Z</option>
					</select>
					<label class="flex items-center gap-2 text-[12px] text-on-surface-variant">
						<input v-model="hideUnavailable" type="checkbox" />
						Hide unavailable
					</label>
					<span class="ml-auto text-[12px] text-on-surface-variant">
						<template v-if="refreshing">Checking availability… · </template>
						{{ roomGroups.length }} room type{{ roomGroups.length === 1 ? "" : "s" }}
					</span>
				</div>

				<p v-if="searched && !options.length" class="text-[13px] text-on-surface-variant">
					Nothing is priced for these dates.
				</p>
				<p
					v-else-if="options.length && !roomGroups.length"
					class="text-[13px] text-on-surface-variant"
				>
					No room types match.
				</p>
				<p v-else-if="!searched" class="text-[13px] text-on-surface-variant">
					{{
						searching
							? "Loading rooms and rates…"
							: "Choose the dates and guests to see rooms and rates."
					}}
				</p>

				<!-- One card per room type, its rate plans as rows -->
				<section class="grid gap-3 2xl:grid-cols-2 2xl:items-start">
					<article
						v-for="group in roomGroups"
						:key="group.room_type"
						class="rounded-xl border bg-surface-container-lowest"
						:class="
							group.rates.some(isSelected)
								? 'border-primary'
								: 'border-outline-variant'
						"
					>
						<header
							class="flex flex-wrap items-baseline justify-between gap-2 border-b border-outline-variant px-4 py-3"
						>
							<h2 class="text-[15px] font-semibold text-on-surface">
								{{ group.room_type_name }}
							</h2>
							<span
								class="text-[12px]"
								:class="
									group.offered
										? group.left <= 2
											? 'font-semibold text-on-tertiary-container'
											: 'text-on-surface-variant'
										: 'text-error'
								"
							>
								<template v-if="group.offered">
									{{ group.left }} left · from
									{{ formatMoney(group.from, group.currency) }}
								</template>
								<template v-else>Not available</template>
							</span>
						</header>
						<ul class="divide-y divide-outline-variant">
							<li
								v-for="option in group.rates"
								:key="option.rate_plan"
								class="px-4 py-3"
								:class="[
									isSelected(option) ? 'bg-primary/5' : '',
									option.offered ? '' : 'opacity-60',
								]"
							>
								<div class="flex flex-wrap items-center justify-between gap-3">
									<div class="min-w-0">
										<p class="text-[13px] font-semibold text-on-surface">
											{{ option.rate_plan_name }}
										</p>
										<p class="text-[11px] text-on-surface-variant">
											<template v-if="option.offered">
												{{
													formatMoney(
														option.average_rate,
														option.currency
													)
												}}
												per night
												<template v-if="option.tax">
													·
													{{
														option.tax_inclusive
															? `incl. tax ${formatMoney(
																	option.tax,
																	option.currency
															  )}`
															: `+ tax ${formatMoney(
																	option.tax,
																	option.currency
															  )}`
													}}
												</template>
											</template>
											<template v-else>{{
												option.reasons.join(", ")
											}}</template>
										</p>
									</div>
									<div class="flex items-center gap-3">
										<p
											v-if="option.offered"
											class="text-[15px] font-semibold text-on-surface"
										>
											{{
												formatMoney(
													option.grand_total || option.total,
													option.currency
												)
											}}
										</p>
										<button
											v-if="option.offered"
											type="button"
											class="rounded-lg border border-primary px-3 py-1.5 text-[12px] font-semibold"
											:class="
												isSelected(option)
													? 'bg-primary text-on-primary'
													: 'text-primary'
											"
											:aria-pressed="isSelected(option)"
											@click="selected = option"
										>
											{{ isSelected(option) ? "Selected" : "Select" }}
										</button>
									</div>
								</div>
								<!-- The nightly prices of the chosen rate, or of a rate that can't be sold. -->
								<div
									v-if="isSelected(option) || !option.offered"
									class="mt-2 flex flex-wrap gap-1.5"
								>
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
							</li>
						</ul>
					</article>
				</section>
			</div>

			<!-- The booking, always beside the results -->
			<aside
				class="xl:sticky xl:top-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
				aria-label="Booking"
			>
				<div>
					<p class="text-[12px] uppercase tracking-wide text-on-surface-variant">
						Booking
					</p>
					<p class="text-[13px] text-on-surface">
						{{ formatNight(arrival) }} → {{ formatNight(departure) }} ·
						{{ nights }} night{{ nights === 1 ? "" : "s" }} · {{ adults }} adult{{
							adults === 1 ? "" : "s"
						}}<span v-if="children">, {{ children }} children</span>
					</p>
				</div>

				<div
					class="rounded-lg border p-3"
					:class="
						selected
							? 'border-primary bg-primary/5'
							: 'border-dashed border-outline-variant'
					"
				>
					<template v-if="selected">
						<p class="text-[14px] font-semibold text-on-surface">
							{{ selected.room_type_name }}
						</p>
						<p class="text-[12px] text-on-surface-variant">
							{{ selected.rate_plan_name }}
						</p>
						<p class="mt-1 text-[18px] font-semibold">
							{{
								formatMoney(
									selected.grand_total || selected.total,
									selected.currency
								)
							}}
							<span
								v-if="selected.tax"
								class="text-[11px] font-normal text-on-surface-variant"
								>{{ selected.tax_inclusive ? "incl." : "with" }} tax
								{{ formatMoney(selected.tax, selected.currency) }}</span
							>
						</p>
						<p
							v-if="searchChanged"
							class="mt-1 text-[11px] font-semibold text-on-tertiary-container"
						>
							{{
								searching || refreshing
									? "Pricing the new dates and guests…"
									: "The dates or guests changed. Refresh to price them."
							}}
						</p>
					</template>
					<p v-else class="text-[12px] text-on-surface-variant">
						No room selected yet. Pick a room and rate from the results.
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
					:disabled="!selected || searchChanged || !guest || !bookingSource || holding"
					@click="holdRooms"
				>
					{{ holding ? "Holding…" : "Hold room" }}
				</button>
				<p
					v-if="!selected || !guest"
					class="text-center text-[11px] text-on-surface-variant"
				>
					{{
						!selected && !guest
							? "Select a room and choose the guest to hold."
							: !selected
							? "Select a room to hold."
							: "Choose the lead guest to hold."
					}}
				</p>
			</aside>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { holdStaysApi, hotelErrorMessage, searchAvailabilityApi } from "@/api/hotel.api";
import GuestPicker from "@/components/hotel/GuestPicker.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useHotelStore } from "@/stores/hotel.store";
import {
	availabilityKey,
	clearAvailability,
	readAvailability,
	writeAvailability,
} from "@/utils/availabilityCache";
import { addDays, formatMoney, formatNight, nightsBetween } from "@/utils/hotelFormat";

const hotel = useHotelStore();
const router = useRouter();

const arrival = ref("");
const departure = ref("");
const adults = ref(2);
const children = ref(0);
// One age per child; an empty age is priced in the oldest child band.
const childAges = ref([]);
watch(children, (count) => {
	const size = Math.max(0, Number(count) || 0);
	childAges.value = Array.from({ length: size }, (_, i) => childAges.value[i] ?? null);
});

function knownAges() {
	return childAges.value.map((age) => (age === "" || age == null ? null : Number(age)));
}
const options = ref([]);
const selected = ref(null);
const guest = ref(null);
const bookingSource = ref("");
const notes = ref("");
const searching = ref(false);
// Results are on screen and being checked again in the background.
const refreshing = ref(false);
let lastRequest = 0;
let searchTimer = null;
const searched = ref(false);
const holding = ref(false);
const error = ref("");
// Filters on the results.
const roomQuery = ref("");
const planFilter = ref("");
const sortBy = ref("price");
const hideUnavailable = ref(false);

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

const ratePlans = computed(() => {
	const plans = new Map();
	for (const option of options.value) plans.set(option.rate_plan, option.rate_plan_name);
	return [...plans].map(([name, label]) => ({ name, label }));
});

/** The results as one entry per room type, with its rate plans, filtered and sorted. */
const roomGroups = computed(() => {
	const text = roomQuery.value.trim().toLowerCase();
	const groups = new Map();
	for (const option of options.value) {
		if (planFilter.value && option.rate_plan !== planFilter.value) continue;
		if (hideUnavailable.value && !option.offered) continue;
		if (text && !`${option.room_type_name} ${option.room_type}`.toLowerCase().includes(text))
			continue;
		if (!groups.has(option.room_type)) {
			groups.set(option.room_type, {
				room_type: option.room_type,
				room_type_name: option.room_type_name,
				currency: option.currency,
				rates: [],
			});
		}
		groups.get(option.room_type).rates.push(option);
	}
	const list = [...groups.values()].map((group) => {
		const offered = group.rates.filter((option) => option.offered);
		const price = (option) => Number(option.grand_total || option.total) || 0;
		group.rates.sort((a, b) => b.offered - a.offered || price(a) - price(b));
		return {
			...group,
			offered: offered.length > 0,
			from: offered.length ? Math.min(...offered.map(price)) : null,
			// Rooms left for the whole stay: the tightest night.
			left: offered.length
				? Math.min(...offered[0].nights.map((night) => Number(night.available) || 0))
				: 0,
		};
	});
	return list.sort((a, b) =>
		sortBy.value === "name"
			? a.room_type_name.localeCompare(b.room_type_name)
			: b.offered - a.offered || (a.from ?? 0) - (b.from ?? 0)
	);
});

// The selection was priced for the searched stay; changing it needs a new search.
const searchChanged = computed(
	() =>
		Boolean(selected.value) &&
		(selected.value.arrival !== arrival.value ||
			selected.value.departure !== departure.value ||
			Number(selected.value.adults) !== Number(adults.value) ||
			Number(selected.value.children || 0) !== Number(children.value || 0))
);

onMounted(async () => {
	await hotel.load();
	resetDates();
	bookingSource.value = hotel.bookingSources.includes("Walk In")
		? "Walk In"
		: hotel.bookingSources[0] || "";
	// Show what's available for tonight straight away; staff refine from there.
	search();
});

watch(propertyName, () => {
	resetDates();
	clearResults();
	search();
});

// Changing the dates or guests searches again, after a short pause for typing.
watch([arrival, departure, adults, children, () => knownAges().join(",")], () => {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(() => search(), 400);
});
onBeforeUnmount(() => clearTimeout(searchTimer));

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
	planFilter.value = "";
}

function isSelected(option) {
	return (
		selected.value?.room_type === option.room_type &&
		selected.value?.rate_plan === option.rate_plan
	);
}

function canSearch() {
	return (
		propertyName.value &&
		arrival.value &&
		departure.value &&
		nights.value >= 1 &&
		Number(adults.value) >= 1
	);
}

/** Show the results, keeping the selected room and rate if it is still on offer. */
function showResults(results) {
	options.value = results;
	searched.value = true;
	if (selected.value) {
		selected.value =
			results.find(
				(option) =>
					option.offered &&
					option.room_type === selected.value.room_type &&
					option.rate_plan === selected.value.rate_plan
			) || null;
	}
	if (planFilter.value && !results.some((option) => option.rate_plan === planFilter.value)) {
		planFilter.value = "";
	}
}

/**
 * Search availability. A recent identical search shows at once from the cache; an older one is
 * shown and checked again in the background. `force` always asks the server (the Search button,
 * and after a hold failed).
 */
async function search({ force = false } = {}) {
	clearTimeout(searchTimer);
	if (!canSearch()) return;
	const params = {
		property: propertyName.value,
		arrival: arrival.value,
		departure: departure.value,
		adults: adults.value,
		children: children.value,
		childAges: knownAges(),
	};
	const key = availabilityKey(params);
	const cached = force ? null : readAvailability(key);
	error.value = "";
	if (cached) {
		showResults(cached.results);
		if (cached.fresh) return;
	}
	const request = ++lastRequest;
	searching.value = !cached;
	refreshing.value = Boolean(cached);
	try {
		const results = (await searchAvailabilityApi(params)) || [];
		if (request !== lastRequest) return; // a newer search started meanwhile
		writeAvailability(key, results);
		showResults(results);
	} catch (e) {
		if (request === lastRequest) error.value = hotelErrorMessage(e);
	} finally {
		if (request === lastRequest) {
			searching.value = false;
			refreshing.value = false;
			searched.value = true;
		}
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
					child_ages: selected.value.child_ages,
					lead_guest: guest.value.name,
					notes: notes.value || null,
				},
			],
			bookingDetails: {
				booking_source: bookingSource.value,
				booker_guest_profile: guest.value.name,
			},
		});
		// The room is held now: every cached search that offered it is out of date.
		clearAvailability();
		router.push({ name: "HotelBooking", params: { bookingId: booking.name } });
	} catch (e) {
		const message = hotelErrorMessage(e);
		await search({ force: true }); // the room may have just sold out: show current availability
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
