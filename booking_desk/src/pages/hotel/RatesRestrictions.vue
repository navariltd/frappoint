<template>
	<div class="px-6 py-5 max-w-[1700px]">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
				<!-- The grid -->
				<section class="min-w-0 space-y-3" aria-label="Rates and restrictions">
					<div class="flex flex-wrap items-end gap-3">
						<label class="text-[12px] text-on-surface-variant">
							Rate plan
							<select v-model="ratePlan" class="grid-input min-w-[220px]">
								<option
									v-for="plan in data?.plans || []"
									:key="plan.name"
									:value="plan.name"
								>
									{{ plan.label }}{{ plan.is_derived ? " (derived)" : "" }}
								</option>
							</select>
						</label>
						<div class="flex items-center gap-1">
							<button
								type="button"
								class="nav-button"
								aria-label="Earlier"
								@click="shift(-days)"
							>
								<span class="material-symbols-outlined text-[18px]"
									>chevron_left</span
								>
							</button>
							<input
								v-model="start"
								type="date"
								class="grid-input !mt-0 w-[150px]"
								aria-label="From"
							/>
							<button
								type="button"
								class="nav-button"
								aria-label="Later"
								@click="shift(days)"
							>
								<span class="material-symbols-outlined text-[18px]"
									>chevron_right</span
								>
							</button>
							<button
								type="button"
								class="rounded-lg px-2 py-1.5 text-[12px] font-semibold text-primary"
								@click="start = data?.business_date || start"
							>
								Today
							</button>
						</div>
						<div
							class="flex rounded-lg border border-outline-variant bg-surface-container-lowest p-0.5"
						>
							<button
								v-for="option in [7, 14, 28]"
								:key="option"
								type="button"
								class="rounded-md px-2.5 py-1 text-[12px] font-semibold"
								:class="
									days === option
										? 'bg-primary text-on-primary'
										: 'text-on-surface-variant'
								"
								@click="days = option"
							>
								{{ option }} days
							</button>
						</div>
						<span v-if="loading" class="text-[12px] text-on-surface-variant"
							>Loading…</span
						>
					</div>

					<p
						v-if="error"
						class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
					>
						{{ error }}
					</p>
					<ActionBanner
						:banner="banner"
						:busy="busy"
						@confirm="confirmBanner"
						@cancel="cancelBanner"
					/>

					<div
						v-if="plan?.is_derived"
						class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-secondary bg-secondary-container/30 px-4 py-3"
					>
						<p class="text-[12px] text-on-surface">
							<span class="material-symbols-outlined align-middle text-[16px]"
								>account_tree</span
							>
							Derived from <b>{{ plan.derivation }}</b
							>. Rates follow the parent; edited nights are kept and marked
							<span
								class="inline-block h-2 w-2 rounded-full bg-tertiary align-middle"
							></span
							>.
							<span v-if="plan.last_derived_on" class="text-on-surface-variant">
								Last worked out {{ formatTimestamp(plan.last_derived_on) }}.</span
							>
						</p>
						<button
							v-if="data.can_edit"
							type="button"
							class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="regenerate"
						>
							Work out again
						</button>
					</div>
					<p
						v-else-if="plan?.children?.length"
						class="text-[12px] text-on-surface-variant"
					>
						{{ plan.children.length }} plan{{
							plan.children.length === 1 ? " is" : "s are"
						}}
						derived from this one and follow its changes.
					</p>

					<div
						v-if="data?.plan"
						class="overflow-x-auto rounded-xl border border-outline-variant bg-surface-container-lowest"
					>
						<table class="w-full border-collapse text-[12px]">
							<thead>
								<tr>
									<th
										class="sticky left-0 z-10 min-w-[150px] bg-surface-container-lowest px-3 py-2 text-left font-semibold"
									>
										Room type
									</th>
									<th
										v-for="column in data.dates"
										:key="column.date"
										class="min-w-[86px] cursor-pointer px-2 py-2 text-center font-semibold"
										:class="[
											isWeekend(column) ? 'bg-surface-container' : '',
											inRange(column.date)
												? 'text-primary'
												: 'text-on-surface',
										]"
										:title="`Select ${column.date}`"
										@click="pickDate(column.date, $event)"
									>
										<span
											class="block text-[10px] font-normal text-on-surface-variant"
											>{{ column.weekday }}</span
										>
										{{ shortDate(column.date) }}
									</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="room in data.room_types"
									:key="room.name"
									class="border-t border-outline-variant"
								>
									<th
										class="sticky left-0 z-10 cursor-pointer bg-surface-container-lowest px-3 py-2 text-left font-semibold"
										:class="
											selectedRooms.includes(room.name)
												? 'text-primary'
												: 'text-on-surface'
										"
										@click="toggleRoom(room.name)"
									>
										{{ room.room_type_name }}
									</th>
									<td
										v-for="column in data.dates"
										:key="column.date"
										class="cursor-pointer border-l border-outline-variant px-2 py-1.5 text-center align-top"
										:class="cellClass(room.name, column)"
										@click="pickCell(room.name, column.date, $event)"
									>
										<template v-if="cell(room.name, column.date)">
											<span class="relative font-semibold text-on-surface">
												{{ money(cell(room.name, column.date).rate) }}
												<span
													v-if="
														cell(room.name, column.date).manual &&
														plan.is_derived
													"
													class="absolute -right-2 top-0 h-1.5 w-1.5 rounded-full bg-tertiary"
													title="Edited by hand: kept when the parent changes"
												></span>
											</span>
										</template>
										<span
											v-else
											class="text-on-surface-variant"
											title="No rate: not sellable on this plan"
											>—</span
										>
										<span
											v-if="restriction(room.name, column.date)"
											class="mt-1 block rounded px-1 py-0.5 text-[10px] font-semibold leading-tight"
											:class="
												restriction(room.name, column.date).closed
													? 'bg-error-container text-on-error-container'
													: 'bg-tertiary-container text-on-tertiary-container'
											"
											:title="`${
												restriction(room.name, column.date).summary
											} (${restriction(room.name, column.date).scope})`"
										>
											{{ restriction(room.name, column.date).summary }}
										</span>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<p
						v-else-if="data && !data.plans.length"
						class="text-[13px] text-on-surface-variant"
					>
						This property has no active nightly rate plans.
					</p>
					<p class="text-[11px] text-on-surface-variant">
						Click a night, a date or a room type to choose what to change; shift-click
						a night or date to choose a range. Restrictions show the rule that applies:
						the most specific of this plan and room, this plan, this room, or the whole
						property.
					</p>
				</section>

				<!-- Edit panel -->
				<aside
					v-if="data?.plan && data.can_edit"
					class="xl:sticky xl:top-4 space-y-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
					aria-label="Change rates or restrictions"
				>
					<div class="grid grid-cols-2 gap-1 rounded-lg bg-surface-container p-1">
						<button
							v-for="tab in ['Rates', 'Restrictions']"
							:key="tab"
							type="button"
							class="rounded-md py-1.5 text-[12px] font-semibold"
							:class="
								mode === tab
									? 'bg-surface-container-lowest shadow-sm'
									: 'text-on-surface-variant'
							"
							@click="mode = tab"
						>
							{{ tab }}
						</button>
					</div>

					<div class="space-y-2">
						<p class="text-[12px] font-semibold text-on-surface">Nights</p>
						<div class="grid grid-cols-2 gap-2">
							<label class="text-[11px] text-on-surface-variant">
								From
								<input v-model="edit.from" type="date" class="grid-input" />
							</label>
							<label class="text-[11px] text-on-surface-variant">
								To
								<input v-model="edit.to" type="date" class="grid-input" />
							</label>
						</div>
						<div class="flex flex-wrap gap-1">
							<button
								v-for="(label, index) in WEEKDAYS"
								:key="label"
								type="button"
								class="rounded border px-2 py-0.5 text-[11px] font-semibold"
								:class="
									edit.weekdays.includes(index)
										? 'border-primary bg-primary text-on-primary'
										: 'border-outline-variant text-on-surface-variant'
								"
								:aria-pressed="edit.weekdays.includes(index)"
								@click="toggleWeekday(index)"
							>
								{{ label }}
							</button>
						</div>
					</div>

					<div class="space-y-1">
						<p class="text-[12px] font-semibold text-on-surface">Room types</p>
						<label
							v-for="room in data.room_types"
							:key="room.name"
							class="flex items-center gap-2 text-[12px] text-on-surface"
						>
							<input
								type="checkbox"
								:checked="selectedRooms.includes(room.name)"
								@change="toggleRoom(room.name)"
							/>
							{{ room.room_type_name }}
						</label>
						<p
							v-if="!selectedRooms.length"
							class="text-[11px] text-on-surface-variant"
						>
							{{
								mode === "Rates"
									? "Choose at least one."
									: "None chosen: every room type."
							}}
						</p>
					</div>

					<!-- Rates -->
					<form v-if="mode === 'Rates'" class="space-y-3" @submit.prevent="applyRates">
						<div class="grid grid-cols-3 gap-1 rounded-lg bg-surface-container p-1">
							<button
								v-for="option in RATE_MODES"
								:key="option.key"
								type="button"
								class="rounded-md py-1 text-[11px] font-semibold"
								:class="
									edit.rateMode === option.key
										? 'bg-surface-container-lowest shadow-sm'
										: 'text-on-surface-variant'
								"
								@click="edit.rateMode = option.key"
							>
								{{ option.label }}
							</button>
						</div>
						<label class="block text-[11px] text-on-surface-variant">
							{{ RATE_MODES.find((option) => option.key === edit.rateMode).hint }}
							<input
								v-model.number="edit.rateValue"
								type="number"
								step="0.01"
								class="grid-input"
							/>
						</label>
						<p v-if="plan.is_derived" class="text-[11px] text-on-tertiary-container">
							On a derived plan these nights become hand-set and stop following the
							parent.
						</p>
						<button
							type="submit"
							class="w-full rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="
								busy ||
								!selectedRooms.length ||
								!validRange ||
								edit.rateValue === '' ||
								edit.rateValue == null
							"
						>
							Apply to {{ nightCount }} night{{ nightCount === 1 ? "" : "s" }}
						</button>
						<button
							v-if="plan.is_derived"
							type="button"
							class="w-full rounded-lg border border-outline-variant px-4 py-2 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy || !selectedRooms.length || !validRange"
							@click="resetOverrides"
						>
							Back to derived rates
						</button>
					</form>

					<!-- Restrictions -->
					<form v-else class="space-y-3" @submit.prevent="applyRestrictions(false)">
						<label class="block text-[11px] text-on-surface-variant">
							Applies to
							<select v-model="edit.scope" class="grid-input">
								<option value="plan">{{ plan.label }} only</option>
								<option value="all">Every rate plan</option>
							</select>
						</label>
						<div class="space-y-1.5">
							<label
								v-for="flag in FLAGS"
								:key="flag.key"
								class="flex items-center gap-2 text-[12px] text-on-surface"
							>
								<input v-model="edit.values[flag.key]" type="checkbox" />
								{{ flag.label }}
							</label>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<label
								v-for="limit in LIMITS"
								:key="limit.key"
								class="text-[11px] text-on-surface-variant"
							>
								{{ limit.label }}
								<input
									v-model.number="edit.values[limit.key]"
									type="number"
									min="0"
									class="grid-input"
									placeholder="—"
								/>
							</label>
						</div>
						<p class="text-[11px] text-on-surface-variant">
							Unticked boxes and empty or 0 limits are turned off on these nights.
						</p>
						<button
							type="submit"
							class="w-full rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="busy || !validRange"
						>
							Set on {{ nightCount }} night{{ nightCount === 1 ? "" : "s" }}
						</button>
						<button
							type="button"
							class="w-full rounded-lg border border-outline-variant px-4 py-2 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy || !validRange"
							@click="applyRestrictions(true)"
						>
							Clear restrictions
						</button>
					</form>
				</aside>
				<aside
					v-else-if="data?.plan"
					class="rounded-xl border border-dashed border-outline-variant p-4 text-[12px] text-on-surface-variant"
				>
					Only Revenue Managers and Hospitality Managers change rates and restrictions.
				</aside>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
	fetchRateGridApi,
	hotelErrorMessage,
	regenerateRatesApi,
	resetRatesApi,
	setRatesApi,
	setRestrictionsApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { addDays, formatMoney } from "@/utils/hotelFormat";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const RATE_MODES = [
	{ key: "rate", label: "Set rate", hint: "New rate per night" },
	{ key: "percent", label: "Adjust %", hint: "Change by a percentage (−10 lowers by 10%)" },
	{ key: "amount", label: "Adjust by", hint: "Change by an amount (−500 lowers by 500)" },
];
const FLAGS = [
	{ key: "closed", label: "Closed (stop sell)" },
	{ key: "closed_to_arrival", label: "Closed to arrival" },
	{ key: "closed_to_departure", label: "Closed to departure" },
];
const LIMITS = [
	{ key: "min_stay_arrival", label: "Min stay, arriving" },
	{ key: "min_stay_through", label: "Min stay, through" },
	{ key: "max_stay", label: "Max stay" },
	{ key: "min_advance_days", label: "Min days ahead" },
	{ key: "max_advance_days", label: "Max days ahead" },
];

const hotel = useHotelStore();
const { banner, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const ratePlan = ref("");
const start = ref("");
const days = ref(14);
const mode = ref("Rates");
const selectedRooms = ref([]);
const edit = reactive({
	from: "",
	to: "",
	weekdays: [0, 1, 2, 3, 4, 5, 6],
	rateMode: "rate",
	rateValue: null,
	scope: "plan",
	values: emptyValues(),
});

const plan = computed(() => data.value?.plan || null);
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});
const validRange = computed(
	() => edit.from && edit.to && edit.from <= edit.to && edit.weekdays.length
);
const nightCount = computed(() => {
	if (!validRange.value) return 0;
	let count = 0;
	for (let night = edit.from; night <= edit.to; night = addDays(night, 1)) {
		if (edit.weekdays.includes(weekdayIndex(night))) count += 1;
	}
	return count;
});

function emptyValues() {
	return Object.fromEntries(
		[...FLAGS, ...LIMITS].map((rule) => [rule.key, FLAGS.includes(rule) ? false : null])
	);
}

function weekdayIndex(night) {
	// Monday is 0, as on the server.
	return (new Date(`${night}T00:00:00`).getDay() + 6) % 7;
}

function money(amount) {
	return formatMoney(amount, plan.value?.currency).replace(/\.00$/, "");
}

function shortDate(night) {
	return new Date(`${night}T00:00:00`).toLocaleDateString(undefined, {
		day: "numeric",
		month: "short",
	});
}

function formatTimestamp(value) {
	return new Date(String(value).replace(" ", "T")).toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function isWeekend(column) {
	return ["Fri", "Sat"].includes(column.weekday);
}

function cell(room, night) {
	return data.value?.rates?.[room]?.[night] || null;
}

function restriction(room, night) {
	return data.value?.restrictions?.[room]?.[night] || null;
}

function inRange(night) {
	return edit.from && edit.to && night >= edit.from && night <= edit.to;
}

function cellClass(room, column) {
	const chosen =
		inRange(column.date) &&
		(!selectedRooms.value.length || selectedRooms.value.includes(room));
	if (chosen) return "bg-primary/10";
	return isWeekend(column) ? "bg-surface-container/60" : "";
}

function pickDate(night, event) {
	if (event?.shiftKey && edit.from) {
		[edit.from, edit.to] = night < edit.from ? [night, edit.from] : [edit.from, night];
	} else {
		edit.from = night;
		edit.to = night;
	}
}

function pickCell(room, night, event) {
	pickDate(night, event);
	if (!event?.shiftKey) selectedRooms.value = [room];
	else if (!selectedRooms.value.includes(room)) selectedRooms.value.push(room);
	const current = cell(room, night);
	if (mode.value === "Rates" && current && !event?.shiftKey) {
		edit.rateMode = "rate";
		edit.rateValue = current.rate;
	}
	const rule = restriction(room, night);
	if (mode.value === "Restrictions" && !event?.shiftKey) {
		edit.values = emptyValues();
		if (rule)
			for (const key of Object.keys(edit.values))
				edit.values[key] = FLAGS.some((f) => f.key === key)
					? !!rule[key]
					: rule[key] || null;
	}
}

function toggleRoom(room) {
	selectedRooms.value = selectedRooms.value.includes(room)
		? selectedRooms.value.filter((name) => name !== room)
		: [...selectedRooms.value, room];
}

function toggleWeekday(index) {
	edit.weekdays = edit.weekdays.includes(index)
		? edit.weekdays.filter((day) => day !== index)
		: [...edit.weekdays, index].sort();
}

function shift(by) {
	start.value = addDays(start.value, by);
}

async function load() {
	if (!hotel.property) return;
	loading.value = true;
	error.value = "";
	try {
		data.value = await fetchRateGridApi({
			property: hotel.property,
			ratePlan: ratePlan.value,
			start: start.value,
			days: days.value,
		});
		if (data.value?.plan && ratePlan.value !== data.value.plan.name)
			ratePlan.value = data.value.plan.name;
		if (!start.value) start.value = data.value?.business_date || "";
		if (!edit.from && data.value?.dates?.length) {
			edit.from = data.value.dates[0].date;
			edit.to = data.value.dates[0].date;
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function run(command, done) {
	busy.value = true;
	error.value = "";
	try {
		const result = await command();
		await load();
		if (done) notify(done(result));
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		busy.value = false;
	}
}

function scopeArgs() {
	return {
		fromDate: edit.from,
		toDate: edit.to,
		weekdays: edit.weekdays,
	};
}

function applyRates() {
	const value = Number(edit.rateValue);
	run(
		() =>
			setRatesApi({
				ratePlan: plan.value.name,
				roomTypes: selectedRooms.value,
				...scopeArgs(),
				rate: edit.rateMode === "rate" ? value : null,
				adjustPercent: edit.rateMode === "percent" ? value : null,
				adjustAmount: edit.rateMode === "amount" ? value : null,
			}),
		(result) => ({
			title: "Rates saved",
			message: `${result.updated} changed, ${result.created} added.${
				plan.value.children?.length ? " Derived plans are being worked out again." : ""
			}`,
		})
	);
}

function resetOverrides() {
	run(
		() =>
			resetRatesApi({
				ratePlan: plan.value.name,
				roomTypes: selectedRooms.value,
				...scopeArgs(),
			}),
		(result) => ({
			title: "Back to derived rates",
			message: `${result.reset} hand-set night${
				result.reset === 1 ? "" : "s"
			} now follow the parent.`,
		})
	);
}

function applyRestrictions(clear) {
	const values = Object.fromEntries(
		Object.entries(edit.values).map(([key, value]) => [
			key,
			typeof value === "boolean" ? (value ? 1 : 0) : Number(value) || 0,
		])
	);
	run(
		() =>
			setRestrictionsApi({
				property: hotel.property,
				ratePlan: edit.scope === "plan" ? plan.value.name : null,
				roomTypes: selectedRooms.value,
				...scopeArgs(),
				values,
				clear,
			}),
		(result) => ({
			title: clear ? "Restrictions cleared" : "Restrictions saved",
			message: `${result.created || 0} added, ${result.updated || 0} changed, ${
				result.deleted || 0
			} removed.`,
		})
	);
}

function regenerate() {
	run(
		() => regenerateRatesApi(plan.value.name),
		() => ({
			title: "Working out the rates again",
			message: "It runs in the background; refresh in a moment to see the new rates.",
		})
	);
}

onMounted(async () => {
	await hotel.load();
	load();
});
watch(
	() => hotel.property,
	() => {
		ratePlan.value = "";
		start.value = "";
		load();
	}
);
watch([ratePlan, start, days], (now, before) => {
	if (now.join() !== before.join()) load();
});
watch(mode, () => (edit.values = emptyValues()));
</script>

<style scoped>
.grid-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
.nav-button {
	@apply flex h-9 w-9 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface-variant;
}
</style>
