<template>
	<div class="px-6 py-5 space-y-5 max-w-6xl">
		<div class="flex justify-end">
			<button
				type="button"
				class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
				@click="load"
			>
				Refresh
			</button>
		</div>

		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<nav class="flex gap-2">
				<button
					v-for="tab in tabs"
					:key="tab.key"
					type="button"
					class="rounded-full px-4 py-1.5 text-[12px] font-semibold border"
					:class="
						activeTab === tab.key
							? 'bg-primary text-on-primary border-primary'
							: 'border-outline-variant text-on-surface'
					"
					@click="activeTab = tab.key"
				>
					{{ tab.label }} · {{ today?.[tab.key]?.length || 0 }}
				</button>
			</nav>

			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>
			<ActionBanner
				:banner="banner"
				:busy="!!busy"
				@confirm="confirmBanner"
				@cancel="cancelBanner"
			/>
			<p v-if="loading && !today" class="text-[13px] text-on-surface-variant">Loading…</p>
			<p v-else-if="today && !rows.length" class="text-[13px] text-on-surface-variant">
				Nothing here today.
			</p>

			<ul
				v-if="rows.length"
				class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
			>
				<li
					v-for="stay in rows"
					:key="stay.name"
					class="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
				>
					<RouterLink :to="{ name: 'HotelStay', params: { stayId: stay.name } }">
						<span class="text-[14px] font-semibold text-on-surface">{{
							stay.lead_guest_name
						}}</span>
						<span class="block text-[12px] text-on-surface-variant">
							{{ stay.name }} · {{ stay.room_type_name }} ·
							{{ formatNight(stay.arrival_date) }} →
							{{ formatNight(stay.departure_date) }}
							<span v-if="stay.eta"> · ETA {{ String(stay.eta).slice(0, 5) }}</span>
						</span>
					</RouterLink>
					<span class="flex items-center gap-3">
						<span
							class="rounded px-2 py-1 text-[12px] font-semibold"
							:class="
								stay.room_number
									? stay.room_ready || activeTab !== 'arrivals'
										? 'bg-secondary-container text-on-secondary-container'
										: 'bg-tertiary-container text-on-tertiary-container'
									: 'bg-surface-container text-on-surface-variant'
							"
						>
							{{ stay.room_number ? `Room ${stay.room_number}` : "No room" }}
							<span v-if="stay.room_number && activeTab === 'arrivals'">
								· {{ stay.room_condition }}</span
							>
						</span>
						<HotelStatusBadge :status="stay.status" />
						<button
							v-if="activeTab === 'arrivals' && stay.room_number && stay.room_ready"
							type="button"
							class="rounded-lg bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy === stay.name"
							@click="run(stay, () => checkInApi(stay.name))"
						>
							Check in
						</button>
						<button
							v-if="activeTab !== 'arrivals'"
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy === stay.name"
							@click="checkOut(stay)"
						>
							Check out
						</button>
						<RouterLink
							:to="{ name: 'HotelStay', params: { stayId: stay.name } }"
							class="text-[12px] font-semibold text-primary"
						>
							Open
						</RouterLink>
					</span>
				</li>
			</ul>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import {
	checkInApi,
	checkOutApi,
	fetchFrontDeskTodayApi,
	hotelErrorMessage,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { formatNight } from "@/utils/hotelFormat";

const hotel = useHotelStore();
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const today = ref(null);
const activeTab = ref("arrivals");
const loading = ref(false);
const busy = ref("");
const error = ref("");

const tabs = [
	{ key: "arrivals", label: "Arrivals" },
	{ key: "in_house", label: "In House" },
	{ key: "departures", label: "Departures" },
];

const propertyName = computed(() => hotel.property);
const rows = computed(() => today.value?.[activeTab.value] || []);
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
		today.value = await fetchFrontDeskTodayApi(propertyName.value);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function run(stay, command) {
	busy.value = stay.name;
	error.value = "";
	let message = "";
	try {
		await command();
	} catch (e) {
		message = `${stay.lead_guest_name}: ${hotelErrorMessage(e)}`;
	} finally {
		busy.value = "";
		// Reload first: loading clears the error, and the message must stay on screen.
		await load();
		error.value = message;
	}
}

async function checkOut(stay) {
	const answer = await ask({
		title: `Check out ${stay.lead_guest_name}?`,
		message: stay.room_number
			? `Room ${stay.room_number} becomes vacant and is marked dirty.`
			: "",
		confirmLabel: "Check out",
	});
	if (answer) run(stay, () => checkOutApi(stay.name));
}

onMounted(async () => {
	await hotel.load();
	load();
});
watch(propertyName, load);
</script>
