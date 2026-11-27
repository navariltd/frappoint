<template>
	<div class="px-6 py-5 max-w-[1800px] space-y-3">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<!-- Toolbar -->
			<div class="flex flex-wrap items-end gap-3">
				<label class="text-[12px] text-on-surface-variant">
					Room type
					<select v-model="roomType" class="chart-input min-w-[180px]">
						<option value="">All room types</option>
						<option
							v-for="type in data?.room_types || []"
							:key="type.name"
							:value="type.name"
						>
							{{ type.room_type_name }}
						</option>
					</select>
				</label>
				<div class="flex items-center gap-1">
					<button
						type="button"
						class="nav-button"
						aria-label="Earlier"
						@click="shift(-step)"
					>
						<span class="material-symbols-outlined text-[18px]">chevron_left</span>
					</button>
					<input
						v-model="start"
						type="date"
						class="chart-input !mt-0 w-[150px]"
						aria-label="From"
					/>
					<button
						type="button"
						class="nav-button"
						aria-label="Later"
						@click="shift(step)"
					>
						<span class="material-symbols-outlined text-[18px]">chevron_right</span>
					</button>
					<button
						type="button"
						class="rounded-lg px-2 py-1.5 text-[12px] font-semibold text-primary"
						@click="goToday"
					>
						Today
					</button>
				</div>
				<div
					class="flex rounded-lg border border-outline-variant bg-surface-container-lowest p-0.5"
					role="group"
					aria-label="Days shown"
				>
					<button
						v-for="option in dayOptions"
						:key="option"
						type="button"
						class="rounded-md px-3 py-1.5 text-[12px] font-semibold"
						:class="
							days === option
								? 'bg-primary text-on-primary'
								: 'text-on-surface-variant hover:bg-surface-container-high'
						"
						@click="days = option"
					>
						{{ option }} days
					</button>
				</div>
				<div class="ml-auto flex items-center gap-3 text-[11px] text-on-surface-variant">
					<span v-if="loadedAt">
						Updated {{ loadedAt }}
						<template v-if="data?.refresh_seconds">
							· every {{ data.refresh_seconds }}s</template
						>
					</span>
					<button
						type="button"
						class="nav-button"
						aria-label="Refresh"
						:disabled="loading"
						@click="load()"
					>
						<span
							class="material-symbols-outlined text-[18px]"
							:class="{ 'animate-spin': loading }"
							>refresh</span
						>
					</button>
				</div>
			</div>

			<!-- Legend -->
			<div class="flex flex-wrap items-center gap-4 text-[11px] text-on-surface-variant">
				<span class="flex items-center gap-1.5"
					><span class="legend bar-assigned"></span> Assigned, not arrived</span
				>
				<span class="flex items-center gap-1.5"
					><span class="legend bar-occupied"></span> In house</span
				>
				<span class="flex items-center gap-1.5"
					><span class="legend bar-released"></span> Checked out, or moved from</span
				>
				<span class="flex items-center gap-1.5"
					><span class="legend outage"></span> Out of order / service</span
				>
				<span class="flex items-center gap-1.5">
					<span class="h-2 w-2 rounded-full bg-[#2e7d32]"></span> Clean
					<span class="h-2 w-2 rounded-full bg-[#f9a825] ml-2"></span> Pickup
					<span class="h-2 w-2 rounded-full bg-[#c62828] ml-2"></span> Dirty
				</span>
				<span v-if="data?.can_move"
					>Drag a stay onto a room to assign or move it, or tap it to pick a room.</span
				>
			</div>

			<!-- With the side panel open, its questions show in the panel instead. -->
			<ActionBanner
				v-if="!selected"
				:banner="banner"
				:busy="busy"
				@confirm="confirmBanner"
				@cancel="cancelBanner"
			/>
			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>

			<!-- Stays without a room -->
			<section
				v-if="data"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
				:class="{
					'ring-2 ring-primary/50': dropTarget === UNASSIGNED,
				}"
				aria-label="Stays without a room"
				@dragover="onDragOver($event, null)"
				@dragleave="onDragLeave(null)"
				@drop="onDrop($event, null)"
			>
				<div class="flex items-center justify-between gap-2">
					<h2 class="text-[13px] font-semibold">
						Without a room
						<span class="font-normal text-on-surface-variant"
							>· {{ visibleUnassigned.length }}</span
						>
					</h2>
					<p class="text-[11px] text-on-surface-variant">
						Drag a stay onto a room, or tap it to pick one. Drop an assigned stay here
						to take its room off.
					</p>
				</div>
				<p
					v-if="!visibleUnassigned.length"
					class="mt-1 text-[12px] text-on-surface-variant"
				>
					Every stay in these dates has a room.
				</p>
				<ul v-else class="mt-2 flex flex-wrap gap-2">
					<li
						v-for="stay in visibleUnassigned"
						:key="stay.stay"
						class="rounded-lg border px-2.5 py-1.5 text-[12px]"
						:class="
							stay.draggable && data.can_move
								? 'border-primary/40 bg-primary/5 cursor-grab'
								: 'border-dashed border-outline-variant text-on-surface-variant'
						"
						:draggable="stay.draggable && data.can_move"
						:title="
							stay.draggable
								? 'Drag onto a room'
								: 'Confirm the hold before giving it a room'
						"
						@dragstart="onDragStart($event, unassignedDrag(stay))"
						@dragend="onDragEnd"
					>
						<button
							type="button"
							class="font-semibold hover:underline"
							draggable="false"
							:aria-label="`Pick a room for ${stay.guest || stay.stay}`"
							@click="select(unassignedDrag(stay))"
						>
							{{ stay.guest || stay.stay }}
						</button>
						<span class="text-on-surface-variant">
							· {{ stay.room_type_name }} · {{ shortDate(stay.arrival) }}–{{
								shortDate(stay.departure)
							}}
							· {{ stay.stay_status }}
						</span>
					</li>
				</ul>
			</section>

			<!-- The chart -->
			<section
				v-if="data"
				class="overflow-auto rounded-xl border border-outline-variant bg-surface-container-lowest max-h-[calc(100vh-260px)]"
				aria-label="Tape chart"
			>
				<div
					class="relative"
					:style="{ width: `${LABEL_WIDTH + cellWidth * columns.length}px` }"
				>
					<!-- Dates -->
					<div
						class="sticky top-0 z-20 flex bg-surface-container-lowest border-b border-outline-variant"
					>
						<div
							class="sticky left-0 z-30 shrink-0 border-r border-outline-variant bg-surface-container-lowest px-3 py-2 text-[11px] font-semibold text-on-surface-variant"
							:style="{ width: `${LABEL_WIDTH}px` }"
						>
							Room
						</div>
						<div
							v-for="column in columns"
							:key="column.date"
							class="shrink-0 border-r border-outline-variant/50 py-1 text-center text-[10px] leading-tight"
							:class="[
								column.date === data.business_date
									? 'bg-primary/10 font-semibold text-primary'
									: isWeekend(column)
									? 'bg-surface-container text-on-surface-variant'
									: 'text-on-surface-variant',
							]"
							:style="{ width: `${cellWidth}px` }"
						>
							<div>{{ column.weekday }}</div>
							<div class="text-[12px] text-on-surface">
								{{ dayNumber(column.date) }}
							</div>
						</div>
					</div>

					<template v-for="group in groups" :key="group.type.name">
						<div
							class="sticky left-0 z-10 flex border-b border-outline-variant bg-surface-container px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant"
							:style="{ width: `${LABEL_WIDTH + cellWidth * columns.length}px` }"
						>
							{{ group.type.room_type_name }}
							<span class="ml-1 font-normal normal-case"
								>· {{ group.rooms.length }} rooms</span
							>
						</div>
						<div
							v-for="room in group.rooms"
							:key="room.name"
							class="relative flex border-b border-outline-variant/50"
							:class="{
								'bg-[#e8f5e9]': dropTarget === room.name && dropOk,
								'bg-error-container/40': dropTarget === room.name && !dropOk,
							}"
							:style="{ height: `${ROW_HEIGHT}px` }"
							@dragover="onDragOver($event, room)"
							@dragleave="onDragLeave(room)"
							@drop="onDrop($event, room)"
						>
							<div
								class="sticky left-0 z-10 flex shrink-0 items-center gap-2 border-r border-outline-variant bg-surface-container-lowest px-3 text-[12px]"
								:style="{ width: `${LABEL_WIDTH}px` }"
							>
								<span
									class="h-2 w-2 shrink-0 rounded-full"
									:style="{
										background: conditionColor(room.housekeeping_condition),
									}"
									:title="room.housekeeping_condition"
								></span>
								<span class="font-semibold">{{ room.room_number }}</span>
								<span class="truncate text-[10px] text-on-surface-variant">
									{{ room.housekeeping_condition }}
									<template v-if="room.floor"> · fl {{ room.floor }}</template>
								</span>
							</div>
							<div
								v-for="column in columns"
								:key="column.date"
								class="shrink-0 border-r border-outline-variant/30"
								:class="{
									'bg-primary/5': column.date === data.business_date,
									'bg-surface-container/40':
										column.date !== data.business_date && isWeekend(column),
								}"
								:style="{ width: `${cellWidth}px` }"
							></div>

							<!-- Out of order / service -->
							<div
								v-for="outage in outagesByRoom[room.name] || []"
								:key="outage.name"
								class="outage absolute top-1 bottom-1 rounded-md text-[10px] font-semibold text-error flex items-center px-2 overflow-hidden"
								:style="spanStyle(outage.from_date, outage.to_date, false)"
								:title="`${outage.state}: ${outage.reason || ''}`"
							>
								<span class="truncate">{{ outage.state }}</span>
							</div>

							<!-- Stays -->
							<div
								v-for="bar in barsByRoom[room.name] || []"
								:key="bar.assignment"
								class="absolute top-1.5 bottom-1.5 flex items-center gap-1 overflow-hidden rounded-md px-2 text-[11px] shadow-sm focus:outline-none focus:ring-2 focus:ring-secondary"
								:class="[
									barClass(bar),
									bar.draggable && data.can_move
										? 'cursor-grab'
										: 'cursor-pointer',
									dragging?.stay === bar.stay ? 'opacity-40' : '',
									selected?.assignment === bar.assignment
										? 'ring-2 ring-secondary'
										: '',
								]"
								:style="spanStyle(bar.start, bar.end, true)"
								:draggable="bar.draggable && data.can_move"
								tabindex="0"
								role="button"
								:aria-label="barLabel(bar)"
								:title="barLabel(bar)"
								@dragstart="onDragStart($event, barDrag(bar))"
								@dragend="onDragEnd"
								@click="select(barDrag(bar))"
								@keydown.enter="select(barDrag(bar))"
								@keydown.space.prevent="select(barDrag(bar))"
							>
								<span
									v-if="bar.locked"
									class="material-symbols-outlined text-[13px]"
									aria-hidden="true"
									>lock</span
								>
								<span class="truncate font-semibold">{{
									bar.guest || bar.stay
								}}</span>
							</div>
						</div>
					</template>

					<p
						v-if="!data.rooms.length"
						class="px-4 py-6 text-[13px] text-on-surface-variant"
					>
						No active rooms{{ roomType ? " of this type" : "" }}.
					</p>
				</div>
			</section>
			<p v-else-if="loading" class="text-[13px] text-on-surface-variant">Loading…</p>

			<!-- Tap a stay: its rooms, ranked, with Assign, Move or Unassign -->
			<TapeChartStayPanel
				v-if="selected && data"
				:target="selected"
				:can-move="data.can_move"
				:busy="busy"
				:banner="banner"
				@confirm="confirmBanner"
				@cancel="cancelBanner"
				@choose="(room) => attempt(selected, room)"
				@unassign="attempt(selected, null)"
				@open="openStay(selected.stay)"
				@close="selected = null"
			/>
		</template>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { checkDropApi, dropStayApi, fetchTapeChartApi, hotelErrorMessage } from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import TapeChartStayPanel from "@/components/hotel/TapeChartStayPanel.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { addDays } from "@/utils/hotelFormat";

const LABEL_WIDTH = 150;
const ROW_HEIGHT = 40;
const UNASSIGNED = "__unassigned__";

const hotel = useHotelStore();
const router = useRouter();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();

const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const loadedAt = ref("");
const start = ref("");
const days = ref(0);
const roomType = ref("");
const dragging = ref(null);
const dropTarget = ref(null);
const dropOk = ref(false);
// The stay opened in the side panel (tapped, or chosen with the keyboard).
const selected = ref(null);
// Conditions a room must be in to take a guest now, per the property (it may require inspection).
const ready = computed(() => data.value?.ready_conditions || ["Clean", "Inspected"]);
let timer = null;

const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

const dayOptions = computed(() => {
	const options = [7, 14, 30];
	const fallback = data.value?.default_days;
	return fallback && !options.includes(fallback)
		? [...options, fallback].sort((a, b) => a - b)
		: options;
});
const step = computed(() => Math.max(1, Math.round((days.value || 14) / 2)));
const columns = computed(() => data.value?.days || []);
// Wider cells when fewer days are shown, so short stays stay readable.
const cellWidth = computed(() => {
	const count = columns.value.length || 14;
	if (count <= 7) return 110;
	if (count <= 14) return 72;
	if (count <= 30) return 44;
	return 34;
});
const columnIndex = computed(() =>
	Object.fromEntries(columns.value.map((column, index) => [column.date, index]))
);

const groups = computed(() => {
	if (!data.value) return [];
	const byType = {};
	data.value.rooms.forEach((room) => (byType[room.room_type] ||= []).push(room));
	return data.value.room_types
		.filter((type) => byType[type.name]?.length)
		.map((type) => ({ type, rooms: byType[type.name] }));
});
const barsByRoom = computed(() => groupBy(data.value?.bars || [], "room"));
const outagesByRoom = computed(() => groupBy(data.value?.outages || [], "room"));
const visibleUnassigned = computed(() => data.value?.unassigned || []);

function groupBy(rows, key) {
	const result = {};
	rows.forEach((row) => (result[row[key]] ||= []).push(row));
	return result;
}

// ------------------------------------------------------------------ drawing

function dayOffset(date) {
	const first = data.value.start;
	const diff = (new Date(`${date}T00:00:00`) - new Date(`${first}T00:00:00`)) / 86400000;
	return Math.round(diff);
}

/** Left and width for [from, to). Stays start mid-arrival-day and end mid-departure-day. */
function spanStyle(from, to, halfDays) {
	const width = columns.value.length;
	const half = halfDays ? 0.5 : 0;
	let left = dayOffset(from) + half;
	let right = dayOffset(to) + half;
	if (right <= left) right = left + 0.25; // a same-day segment still shows
	left = Math.max(left, 0);
	right = Math.min(right, width);
	return {
		left: `${LABEL_WIDTH + left * cellWidth.value + 1}px`,
		width: `${Math.max((right - left) * cellWidth.value - 2, 6)}px`,
	};
}

function barClass(bar) {
	if (bar.status === "Released") return "bar-released";
	if (bar.status === "Occupied") return "bar-occupied";
	return "bar-assigned";
}

function barLabel(bar) {
	const state =
		bar.status === "Released"
			? bar.stay_status === "Checked Out"
				? "checked out"
				: "moved to another room"
			: bar.status === "Occupied"
			? "in house"
			: "assigned";
	const lock = bar.locked ? ", locked to this room" : "";
	return `${bar.guest || bar.stay}, ${shortDate(bar.arrival)} to ${shortDate(
		bar.departure
	)}, ${state}${lock}. ${bar.stay}`;
}

function conditionColor(condition) {
	return (
		{ Inspected: "#2e7d32", Clean: "#2e7d32", Pickup: "#f9a825", Dirty: "#c62828" }[
			condition
		] || "#9e9e9e"
	);
}

function isWeekend(column) {
	return ["Fri", "Sat"].includes(column.weekday);
}

function dayNumber(date) {
	return Number(String(date).slice(8, 10));
}

function shortDate(date) {
	if (!date) return "";
	return new Date(`${String(date).slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, {
		day: "numeric",
		month: "short",
	});
}

function openStay(stay) {
	if (dragging.value) return;
	router.push({ name: "HotelStay", params: { stayId: stay } });
}

// ------------------------------------------------------------------ drag and drop

function barDrag(bar) {
	const room = data.value.rooms.find((row) => row.name === bar.room);
	const moving = bar.status === "Occupied";
	return {
		stay: bar.stay,
		assignment: bar.assignment,
		guest: bar.guest,
		room: bar.room,
		roomNumber: room?.room_number,
		roomType: room?.room_type,
		action: moving ? "move" : "assign",
		arrival: bar.arrival,
		canChange: bar.draggable,
		why: bar.locked
			? "The room is locked to this stay (Do Not Move). Unlock it on the stay page first."
			: bar.status === "Released"
			? "An earlier room of this stay. Open the stay to see its rooms."
			: "This stay can't change rooms now.",
		// A move takes the new room from today; an assignment for the whole stay.
		from: moving ? data.value.business_date : bar.arrival,
		to: bar.departure,
	};
}

function unassignedDrag(stay) {
	return {
		stay: stay.stay,
		guest: stay.guest,
		room: null,
		roomType: stay.room_type,
		action: "assign",
		arrival: stay.arrival,
		canChange: stay.draggable,
		why: "Confirm the hold before giving it a room.",
		from: stay.arrival,
		to: stay.departure,
	};
}

function onDragStart(event, payload) {
	if (!event.target.draggable) return;
	dragging.value = payload;
	event.dataTransfer.effectAllowed = "move";
	event.dataTransfer.setData("text/plain", payload.stay);
}

function onDragEnd() {
	dragging.value = null;
	dropTarget.value = null;
}

/** A quick look on the client, for the colour of the row; the server decides on drop. */
function localProblem(room, drag = dragging.value) {
	if (!room) return drag.room ? "" : "This stay has no room yet.";
	if (room.name === drag.room) return "Already in this room.";
	if (room.room_type !== drag.roomType) return "A different room type.";
	if (drag.action === "move" && !ready.value.includes(room.housekeeping_condition)) {
		return `Room ${room.room_number} is ${room.housekeeping_condition}.`;
	}
	const overlaps = (from, to) => from < drag.to && to > drag.from;
	const taken = (barsByRoom.value[room.name] || []).some(
		(bar) =>
			bar.stay !== drag.stay && bar.status !== "Released" && overlaps(bar.start, bar.end)
	);
	if (taken) return `Room ${room.room_number} is taken on some of these nights.`;
	const closed = (outagesByRoom.value[room.name] || []).some((outage) =>
		overlaps(outage.from_date, outage.to_date)
	);
	return closed ? `Room ${room.room_number} is out of order on some of these nights.` : "";
}

function onDragOver(event, room) {
	if (!dragging.value) return;
	if (!room && !dragging.value.room) return; // already unassigned
	event.preventDefault();
	dropTarget.value = room ? room.name : UNASSIGNED;
	dropOk.value = !localProblem(room);
	event.dataTransfer.dropEffect = dropOk.value ? "move" : "none";
}

function onDragLeave(room) {
	const key = room ? room.name : UNASSIGNED;
	if (dropTarget.value === key) dropTarget.value = null;
}

async function onDrop(event, room) {
	event.preventDefault();
	const drag = dragging.value;
	onDragEnd();
	if (!drag || (!room && !drag.room)) return;
	const problem = localProblem(room);
	if (problem) {
		notify({ title: "That room can't take this stay", message: problem, tone: "danger" });
		return;
	}
	await attempt(drag, room);
}

function select(payload) {
	if (dragging.value) return;
	// A notice from the last change belongs to that stay, not the one being opened.
	if (banner.value?.kind === "notice") cancelBanner();
	selected.value = payload;
}

/**
 * Assign, move or unassign: from a drop or from the side panel. The server checks the room, a
 * Required preference it misses asks for a reason, the user confirms, then the same front-desk
 * command as the stay page runs.
 */
async function attempt(drag, room) {
	busy.value = true;
	error.value = "";
	let check;
	try {
		check = await checkDropApi(drag.stay, room?.name);
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
		return;
	} finally {
		busy.value = false;
	}
	if (!check.allowed) {
		notify({ title: "That move isn't possible", message: check.reason, tone: "danger" });
		return;
	}
	const who = drag.guest || drag.stay;
	// How the room fits the guest's preferences (ranked as on the stay page).
	const fit = check.preference;
	const fitText = fit
		? [
				fit.rank ? `Ranked ${fit.rank} for the guest.` : "",
				fit.matched.length ? `Matches ${fit.matched.join(", ")}.` : "",
				fit.missed.length ? `Misses ${fit.missed.join(", ")}.` : "",
		  ]
				.filter(Boolean)
				.join(" ")
		: "";
	const warnings = [fitText, ...(check.warnings || [])].filter(Boolean).join(" ");
	// A room that misses a Required preference needs a reason first, as on the stay page.
	let preferenceOverrideReason = null;
	if (check.needs_override) {
		const override = await ask({
			title: `Room ${room.room_number} has no ${fit.required_missed.join(", ")}`,
			message: "The guest requires it. Give the reason to use this room anyway.",
			reasonLabel: "Reason",
			reasonPlaceholder: "Guest agreed to this room",
			confirmLabel: `Use ${room.room_number}`,
			tone: "warning",
		});
		if (!override) return;
		preferenceOverrideReason = override.reason;
	}
	const question =
		check.action === "unassign"
			? {
					title: `Take room ${drag.roomNumber} off ${who}'s stay?`,
					message: "The stay goes back to the stays without a room.",
					confirmLabel: "Unassign",
			  }
			: check.action === "move"
			? {
					title: `Move ${who} to room ${room.room_number} now?`,
					message: `The guest's room ${drag.roomNumber} is released and needs cleaning. ${warnings}`,
					reasonLabel: "Why are they moving?",
					reasonOptions: data.value.move_reasons,
					confirmLabel: "Move guest",
			  }
			: {
					title: `Give ${who} room ${room.room_number}?`,
					message: `${shortDate(drag.from)} to ${shortDate(drag.to)}${
						drag.roomNumber ? `, instead of room ${drag.roomNumber}` : ""
					}. ${warnings}`,
					confirmLabel: "Assign room",
			  };
	const answer = await ask(question);
	if (!answer) return;
	busy.value = true;
	try {
		await dropStayApi({
			stay: drag.stay,
			room: room?.name,
			moveReason: check.action === "move" ? answer.reason : null,
			preferenceOverrideReason,
		});
		selected.value = null;
		await load({ quiet: true });
		notify({
			title:
				check.action === "unassign"
					? `${who} has no room now`
					: `${who} is in room ${room.room_number}`,
			tone: "info",
		});
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
		await load({ quiet: true });
	} finally {
		busy.value = false;
	}
}

// ------------------------------------------------------------------ loading

async function load({ quiet = false } = {}) {
	if (!hotel.property) return;
	if (!quiet) loading.value = true;
	try {
		const result = await fetchTapeChartApi({
			property: hotel.property,
			start: start.value,
			days: days.value,
			roomType: roomType.value,
		});
		data.value = result;
		if (!days.value) days.value = result.days.length;
		if (!start.value) start.value = String(result.start);
		loadedAt.value = new Date().toLocaleTimeString(undefined, {
			hour: "2-digit",
			minute: "2-digit",
		});
		if (!quiet) error.value = "";
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
	} finally {
		loading.value = false;
		schedule();
	}
}

/** Refresh on the board interval, but never while someone is dragging or answering. */
function schedule() {
	clearTimeout(timer);
	const seconds = data.value?.refresh_seconds;
	if (!seconds) return;
	timer = setTimeout(() => {
		if (dragging.value || banner.value?.kind === "ask" || busy.value || document.hidden) {
			schedule();
			return;
		}
		load({ quiet: true });
	}, seconds * 1000);
}

function shift(amount) {
	start.value = addDays(start.value || data.value?.start, amount);
}

function goToday() {
	// Yesterday too, so this morning's departures show.
	start.value = addDays(data.value?.business_date, -1);
}

// The first load fills in the window; only later changes by the user load again.
watch([start, days, roomType], (_current, previous) => {
	if (previous.every((value) => value === "" || value === 0)) return;
	load();
});
watch(
	() => hotel.property,
	() => {
		start.value = "";
		days.value = 0;
		roomType.value = "";
		load();
	}
);

onMounted(async () => {
	await hotel.load();
	load();
});
onBeforeUnmount(() => clearTimeout(timer));
</script>

<style scoped>
.chart-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
.nav-button {
	@apply flex h-9 w-9 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface-variant;
}
.bar-assigned {
	@apply bg-primary/15 text-on-surface border border-primary/40;
}
.bar-occupied {
	@apply bg-primary text-on-primary;
}
.bar-released {
	@apply bg-surface-container-high text-on-surface-variant border border-dashed border-outline-variant;
}
.legend {
	@apply inline-block h-3 w-6 rounded-sm;
}
.outage {
	background: repeating-linear-gradient(
		135deg,
		rgb(198 40 40 / 0.12),
		rgb(198 40 40 / 0.12) 6px,
		rgb(198 40 40 / 0.04) 6px,
		rgb(198 40 40 / 0.04) 12px
	);
	border: 1px solid rgb(198 40 40 / 0.35);
}
</style>
