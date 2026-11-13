<template>
	<div class="px-6 py-5 max-w-[1600px]">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<div
			v-else
			class="grid gap-5 lg:grid-cols-[minmax(320px,400px)_minmax(0,1fr)] lg:items-start"
		>
			<!-- Today's list. On small screens it gives way to the selected stay. -->
			<section
				class="space-y-3 lg:sticky lg:top-4"
				:class="{ 'hidden lg:block': selectedId }"
				aria-label="Today"
			>
				<nav class="grid grid-cols-3 gap-1 rounded-xl bg-surface-container p-1">
					<button
						v-for="tab in tabs"
						:key="tab.key"
						type="button"
						class="rounded-lg px-2 py-2 text-center"
						:class="
							activeTab === tab.key
								? 'bg-surface-container-lowest text-on-surface shadow-sm'
								: 'text-on-surface-variant hover:text-on-surface'
						"
						:aria-pressed="activeTab === tab.key"
						@click="activeTab = tab.key"
					>
						<span class="block text-[18px] font-semibold leading-tight">{{
							today?.[tab.key]?.length || 0
						}}</span>
						<span class="block text-[11px] font-semibold">{{ tab.label }}</span>
					</button>
				</nav>

				<div class="flex items-center gap-2">
					<label class="relative block flex-1">
						<span
							class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
							aria-hidden="true"
							>search</span
						>
						<input
							v-model="search"
							type="search"
							class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-[13px] text-on-surface"
							placeholder="Guest, room or reservation"
							aria-label="Search today's stays"
						/>
					</label>
					<button
						type="button"
						class="material-symbols-outlined shrink-0 rounded-lg border border-outline-variant bg-surface-container-lowest p-2 text-[18px] text-on-surface-variant disabled:opacity-50"
						:disabled="loading"
						title="Refresh"
						aria-label="Refresh"
						@click="load"
					>
						refresh
					</button>
				</div>

				<p
					v-if="error"
					class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
				>
					{{ error }}
				</p>
				<ActionBanner
					:banner="banner"
					:busy="!!busy"
					@confirm="confirmBanner"
					@cancel="cancelBanner"
				/>
				<p v-if="loading && !today" class="text-[13px] text-on-surface-variant">
					Loading…
				</p>
				<p v-else-if="today && !rows.length" class="text-[13px] text-on-surface-variant">
					{{ search.trim() ? "No stays match." : emptyText }}
				</p>

				<ul
					v-if="rows.length"
					class="divide-y divide-outline-variant overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest lg:max-h-[calc(100vh-17rem)] lg:overflow-y-auto"
				>
					<li
						v-for="stay in rows"
						:key="stay.name"
						class="border-l-[3px] transition-colors"
						:class="
							stay.name === selectedId
								? 'border-l-primary bg-primary/5'
								: 'border-l-transparent hover:bg-surface-container'
						"
					>
						<RouterLink
							:to="{ name: 'FrontDeskStay', params: { stayId: stay.name } }"
							class="block px-4 pt-3"
							:aria-current="stay.name === selectedId ? 'page' : undefined"
						>
							<span class="flex items-start justify-between gap-3">
								<span class="truncate text-[14px] font-semibold text-on-surface">{{
									stay.lead_guest_name
								}}</span>
								<HotelStatusBadge :status="stay.status" />
							</span>
							<span class="block text-[12px] text-on-surface-variant">
								{{ stay.room_type_name }} · {{ formatNight(stay.arrival_date) }} →
								{{ formatNight(stay.departure_date) }}
								<span v-if="stay.eta">
									· ETA {{ String(stay.eta).slice(0, 5) }}</span
								>
							</span>
						</RouterLink>
						<div class="flex items-center justify-between gap-2 px-4 pb-3 pt-2">
							<span
								class="rounded px-2 py-0.5 text-[11px] font-semibold"
								:class="roomTone(stay)"
							>
								{{ stay.room_number ? `Room ${stay.room_number}` : "No room" }}
								<span v-if="stay.room_number && activeTab === 'arrivals'">
									· {{ stay.room_condition }}</span
								>
							</span>
							<button
								v-if="
									activeTab === 'arrivals' && stay.room_number && stay.room_ready
								"
								type="button"
								class="rounded-lg bg-primary text-on-primary px-3 py-1 text-[12px] font-semibold disabled:opacity-50"
								:disabled="busy === stay.name"
								@click="run(stay, () => checkInApi(stay.name))"
							>
								Check in
							</button>
							<button
								v-else-if="activeTab !== 'arrivals'"
								type="button"
								class="rounded-lg border border-outline-variant px-3 py-1 text-[12px] font-semibold disabled:opacity-50"
								:disabled="busy === stay.name"
								@click="checkOut(stay)"
							>
								Check out
							</button>
							<RouterLink
								v-else
								:to="{ name: 'FrontDeskStay', params: { stayId: stay.name } }"
								class="text-[12px] font-semibold text-primary"
							>
								{{ stay.room_number ? "Get the room ready" : "Assign a room" }} →
							</RouterLink>
						</div>
					</li>
				</ul>
			</section>

			<!-- The selected stay -->
			<section v-if="selectedId" class="min-w-0 space-y-3" aria-label="Selected stay">
				<RouterLink
					:to="{ name: 'FrontDeskToday' }"
					class="text-[12px] font-semibold text-primary lg:hidden"
				>
					← Today
				</RouterLink>
				<div
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-5"
				>
					<ReservationStay
						:key="`${selectedId}:${refreshKey}`"
						:stay-id="selectedId"
						embedded
						@changed="load"
					/>
				</div>
			</section>
			<section
				v-else
				class="hidden min-h-[320px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-outline-variant text-center lg:flex"
			>
				<span
					class="material-symbols-outlined text-[36px] text-on-surface-variant"
					aria-hidden="true"
					>concierge</span
				>
				<p class="text-[14px] font-semibold text-on-surface">Select a guest</p>
				<p class="max-w-xs text-[12px] text-on-surface-variant">
					Their room, guests, folios and deposit open here: assign a room, register,
					check in or out without leaving the list.
				</p>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
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
import ReservationStay from "@/pages/hotel/ReservationStay.vue";
import { useHotelStore } from "@/stores/hotel.store";
import { formatNight } from "@/utils/hotelFormat";

const route = useRoute();
const hotel = useHotelStore();
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const today = ref(null);
const activeTab = ref("arrivals");
const loading = ref(false);
const busy = ref("");
const error = ref("");
const search = ref("");
// Bumped when a list action (check in, check out) changes the selected stay, to reload its pane.
const refreshKey = ref(0);
const selectedId = computed(() => route.params.stayId || null);

const tabs = [
	{ key: "arrivals", label: "Arrivals" },
	{ key: "in_house", label: "In House" },
	{ key: "departures", label: "Departures" },
];

const propertyName = computed(() => hotel.property);
const rows = computed(() => {
	const text = search.value.trim().toLowerCase();
	const list = today.value?.[activeTab.value] || [];
	if (!text) return list;
	return list.filter((stay) =>
		[stay.lead_guest_name, stay.name, stay.room_number, stay.room_type_name]
			.filter(Boolean)
			.some((value) => String(value).toLowerCase().includes(text))
	);
});
const emptyText = computed(
	() =>
		({
			arrivals: "No arrivals left today.",
			in_house: "No guests in house.",
			departures: "No departures today.",
		}[activeTab.value])
);

/** Show the tab the selected stay is on, e.g. In House once it has checked in. */
function followSelected() {
	if (!selectedId.value || !today.value) return;
	const onTab = (key) => (today.value[key] || []).some((stay) => stay.name === selectedId.value);
	if (onTab(activeTab.value)) return;
	const tab = tabs.find((option) => onTab(option.key));
	if (tab) activeTab.value = tab.key;
}

function roomTone(stay) {
	if (!stay.room_number) return "bg-surface-container text-on-surface-variant";
	if (activeTab.value === "arrivals" && !stay.room_ready)
		return "bg-tertiary-container text-on-tertiary-container";
	return "bg-secondary-container text-on-secondary-container";
}
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
		followSelected();
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
		if (stay.name === selectedId.value) refreshKey.value += 1;
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
