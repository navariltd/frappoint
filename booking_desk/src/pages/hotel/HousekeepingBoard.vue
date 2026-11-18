<template>
	<div class="px-3 sm:px-6 py-4 max-w-[1500px] space-y-3">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<!-- Summary -->
			<div class="flex flex-wrap items-center gap-2">
				<button
					v-for="chip in summary"
					:key="chip.key"
					type="button"
					class="flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-semibold"
					:class="
						conditionFilter === chip.key
							? 'border-primary bg-primary text-on-primary'
							: 'border-outline-variant bg-surface-container-lowest text-on-surface'
					"
					@click="toggleFilter(chip.key)"
				>
					<span
						v-if="chip.color"
						class="h-2 w-2 rounded-full"
						:style="{ background: chip.color }"
					></span>
					{{ chip.label }} <span class="font-normal">{{ chip.count }}</span>
				</button>
				<span class="ml-auto text-[11px] text-on-surface-variant">
					{{ data ? formatNight(data.date) : "" }}
					<template v-if="loadedAt"> · updated {{ loadedAt }}</template>
				</span>
				<button
					type="button"
					class="flex h-9 w-9 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-lowest"
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

			<!-- Tabs -->
			<div
				class="flex gap-1 overflow-x-auto rounded-xl border border-outline-variant bg-surface-container-lowest p-1"
				role="tablist"
			>
				<button
					v-for="option in tabs"
					:key="option.key"
					type="button"
					role="tab"
					:aria-selected="tab === option.key"
					class="flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-[13px] font-semibold"
					:class="
						tab === option.key
							? 'bg-primary text-on-primary'
							: 'text-on-surface-variant hover:bg-surface-container-high'
					"
					@click="tab = option.key"
				>
					{{ option.label }}
					<span v-if="option.count" class="ml-1 opacity-80">{{ option.count }}</span>
				</button>
			</div>

			<ActionBanner
				:banner="banner"
				:busy="busy"
				@confirm="confirmBanner"
				@cancel="cancelBanner"
			/>
			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>

			<template v-if="data">
				<!-- My tasks: the attendant's phone view -->
				<section v-if="tab === 'mine'" class="space-y-3" aria-label="My tasks">
					<p v-if="!myTasks.length" class="text-[13px] text-on-surface-variant">
						Nothing assigned to you right now.
					</p>
					<article
						v-for="task in myTasks"
						:key="task.name"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
					>
						<TaskHeading :task="task" :room="roomByName[task.hotel_room]" />
						<div class="grid grid-cols-2 gap-2">
							<button
								v-if="task.status === 'Open'"
								type="button"
								class="big-button bg-primary text-on-primary col-span-2"
								:disabled="busy"
								@click="run(() => startHousekeepingTaskApi(task.name))"
							>
								<span class="material-symbols-outlined">play_arrow</span> Start
							</button>
							<template v-if="task.status === 'In Progress'">
								<button
									type="button"
									class="big-button bg-primary text-on-primary"
									:disabled="busy"
									@click="finish(task, 'Vacant')"
								>
									<span class="material-symbols-outlined">check</span> Done,
									empty
								</button>
								<button
									type="button"
									class="big-button bg-primary/15 text-primary"
									:disabled="busy"
									@click="finish(task, 'Occupied')"
								>
									<span class="material-symbols-outlined">check</span> Done,
									guest things in
								</button>
							</template>
							<button
								v-if="['Open', 'In Progress'].includes(task.status)"
								type="button"
								class="big-button border border-outline-variant"
								:disabled="busy"
								@click="run(() => markDoNotDisturbApi(task.name))"
							>
								<span class="material-symbols-outlined">do_not_disturb_on</span> Do
								Not Disturb
							</button>
							<button
								v-if="data.can_report"
								type="button"
								class="big-button border border-outline-variant"
								@click="openReport(task.hotel_room)"
							>
								<span class="material-symbols-outlined">build</span> Report issue
							</button>
						</div>
					</article>
				</section>

				<!-- Rooms -->
				<section v-if="tab === 'rooms'" class="space-y-3" aria-label="Rooms">
					<div
						class="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8"
					>
						<button
							v-for="room in visibleRooms"
							:key="room.name"
							type="button"
							class="rounded-xl border p-3 text-left space-y-1 focus:outline-none focus:ring-2 focus:ring-secondary"
							:class="[
								conditionClass(room.housekeeping_condition),
								selectedRoom === room.name ? 'ring-2 ring-primary' : '',
							]"
							@click="selectedRoom = selectedRoom === room.name ? '' : room.name"
						>
							<div class="flex items-center justify-between">
								<span class="text-[18px] font-semibold">{{
									room.room_number
								}}</span>
								<span class="flex gap-0.5">
									<span
										v-if="room.arrival_today"
										class="material-symbols-outlined text-[16px]"
										title="Arrival today"
										>login</span
									>
									<span
										v-if="room.departure_today"
										class="material-symbols-outlined text-[16px]"
										title="Departure today"
										>logout</span
									>
									<span
										v-if="room.maintenance.length"
										class="material-symbols-outlined text-[16px] text-error"
										title="Open maintenance"
										>build</span
									>
								</span>
							</div>
							<p class="text-[11px] font-semibold">
								{{ room.housekeeping_condition }}
							</p>
							<p class="text-[11px] opacity-80">
								{{ room.occupancy_status }}
								<template v-if="room.sellability !== 'Sellable'">
									· {{ room.sellability }}</template
								>
							</p>
						</button>
					</div>

					<!-- The selected room -->
					<div
						v-if="selected"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
					>
						<div class="flex items-start justify-between gap-2">
							<div>
								<h2 class="text-[16px] font-semibold">
									Room {{ selected.room_number }}
									<span class="text-[12px] font-normal text-on-surface-variant">
										· {{ selected.room_type_name }}
										<template v-if="selected.floor">
											· floor {{ selected.floor }}</template
										>
									</span>
								</h2>
								<p class="text-[12px] text-on-surface-variant">
									{{ selected.housekeeping_condition }} ·
									{{ selected.occupancy_status }} ·
									{{ selected.ready ? "ready for a guest" : "not ready yet" }}
								</p>
							</div>
							<button
								type="button"
								class="text-[12px] font-semibold text-on-surface-variant"
								@click="selectedRoom = ''"
							>
								Close
							</button>
						</div>
						<ul class="space-y-2">
							<li
								v-for="task in tasksForRoom(selected.name)"
								:key="task.name"
								class="rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
							>
								<TaskRow
									:task="task"
									:data="data"
									:busy="busy"
									@assign="assign"
									@inspect="inspect"
									@cancel="cancelTask"
									@start="(row) => run(() => startHousekeepingTaskApi(row.name))"
									@finish="(row) => finish(row)"
								/>
							</li>
						</ul>
						<p
							v-for="request in selected.maintenance"
							:key="request.issue"
							class="text-[12px] text-error"
						>
							Maintenance: {{ request.issue }} ({{ request.severity }})
						</p>
						<form
							v-if="data.can_supervise"
							class="grid gap-2 sm:grid-cols-4 items-end"
							@submit.prevent="addTask"
						>
							<label class="text-[12px] text-on-surface-variant">
								Add a task
								<select v-model="newTask.type" class="board-input">
									<option
										v-for="type in data.task_types"
										:key="type"
										:value="type"
									>
										{{ type }}
									</option>
								</select>
							</label>
							<label class="text-[12px] text-on-surface-variant">
								Priority
								<select v-model="newTask.priority" class="board-input">
									<option>High</option>
									<option>Normal</option>
									<option>Low</option>
								</select>
							</label>
							<label class="text-[12px] text-on-surface-variant">
								Notes
								<input v-model="newTask.notes" class="board-input" />
							</label>
							<button
								type="submit"
								class="big-button bg-primary text-on-primary"
								:disabled="busy"
							>
								Add
							</button>
						</form>
						<button
							v-if="data.can_report"
							type="button"
							class="text-[12px] font-semibold text-primary"
							@click="openReport(selected.name)"
						>
							Report an issue in this room
						</button>
					</div>
				</section>

				<!-- Tasks: the supervisor's view -->
				<section v-if="tab === 'tasks'" class="space-y-4" aria-label="Tasks">
					<div class="flex flex-wrap items-center gap-2">
						<button
							type="button"
							class="rounded-lg border border-primary px-3 py-2 text-[12px] font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							@click="run(() => planStayoversApi(hotel.property))"
						>
							Plan today's stayovers
						</button>
						<span class="text-[12px] text-on-surface-variant">
							A stayover for every occupied room whose guest stays tonight.
						</span>
					</div>

					<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
						<div class="space-y-4">
							<div v-for="group in taskGroups" :key="group.label" class="space-y-2">
								<h2 class="text-[13px] font-semibold">
									{{ group.label }}
									<span class="font-normal text-on-surface-variant"
										>· {{ group.tasks.length }}</span
									>
								</h2>
								<ul
									v-if="group.tasks.length"
									class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
								>
									<li
										v-for="task in group.tasks"
										:key="task.name"
										class="px-3 py-2 text-[13px]"
									>
										<TaskRow
											:task="task"
											:data="data"
											:busy="busy"
											show-room
											@assign="assign"
											@inspect="inspect"
											@cancel="cancelTask"
											@start="
												(row) =>
													run(() => startHousekeepingTaskApi(row.name))
											"
											@finish="(row) => finish(row)"
										/>
									</li>
								</ul>
							</div>
						</div>

						<aside class="space-y-4">
							<section
								class="rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
							>
								<h2 class="text-[13px] font-semibold">Team today</h2>
								<p
									v-if="!data.staff.length"
									class="text-[12px] text-on-surface-variant"
								>
									No employees found. Set the Housekeeping Department on the
									property.
								</p>
								<ul class="mt-2 space-y-1.5 text-[12px]">
									<li
										v-for="person in data.staff"
										:key="person.employee"
										class="flex items-center justify-between gap-2"
									>
										<span>
											<span
												class="mr-1 inline-block h-2 w-2 rounded-full"
												:class="
													person.on_shift
														? 'bg-[#2e7d32]'
														: 'bg-outline-variant'
												"
											></span>
											{{ person.employee_name }}
											<span
												v-if="!person.on_shift"
												class="text-on-surface-variant"
												>(off shift)</span
											>
										</span>
										<span class="text-on-surface-variant">
											{{ person.credits }} credits · {{ person.open }} open
										</span>
									</li>
								</ul>
							</section>
							<section
								class="rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
							>
								<h2 class="text-[13px] font-semibold">
									Front desk vs housekeeping
								</h2>
								<p
									v-if="!data.discrepancies.length"
									class="text-[12px] text-on-surface-variant"
								>
									No disagreements today.
								</p>
								<ul class="mt-2 space-y-2 text-[12px]">
									<li v-for="row in data.discrepancies" :key="row.room">
										<b>Room {{ row.room_number }}: {{ row.kind }}</b>
										<span class="block text-on-surface-variant">
											Front desk: {{ row.front_desk }}.
											{{ row.hint }} Reported by
											{{ row.reported_by || "housekeeping" }}.
										</span>
									</li>
								</ul>
							</section>
						</aside>
					</div>
				</section>

				<!-- Maintenance -->
				<section v-if="tab === 'maintenance'" class="space-y-3" aria-label="Maintenance">
					<button
						v-if="data.can_report && !report.open"
						type="button"
						class="rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-on-primary"
						@click="openReport('')"
					>
						Report an issue
					</button>
					<form
						v-if="report.open"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 grid gap-3 sm:grid-cols-2"
						@submit.prevent="submitReport"
					>
						<label class="text-[12px] text-on-surface-variant">
							Room
							<select v-model="report.room" class="board-input">
								<option value="">No room (equipment elsewhere)</option>
								<option
									v-for="room in data.rooms"
									:key="room.name"
									:value="room.name"
								>
									{{ room.room_number }} · {{ room.room_type_name }}
								</option>
							</select>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							What is wrong?
							<input v-model="report.issue" required class="board-input" />
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Severity
							<select v-model="report.severity" class="board-input">
								<option>Low</option>
								<option>Medium</option>
								<option>High</option>
								<option>Critical</option>
							</select>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Can the room be sold?
							<select
								v-model="report.roomImpact"
								class="board-input"
								:disabled="!report.room"
							>
								<option value="None">Yes</option>
								<option value="Out of Service">No, out of service</option>
								<option value="Out of Order">
									No, out of order (leaves inventory)
								</option>
							</select>
						</label>
						<template v-if="report.roomImpact !== 'None'">
							<label class="text-[12px] text-on-surface-variant">
								Out from
								<input v-model="report.outFrom" type="date" class="board-input" />
							</label>
							<label class="text-[12px] text-on-surface-variant">
								Expected back on
								<input v-model="report.backOn" type="date" class="board-input" />
							</label>
							<p
								v-if="
									report.roomImpact === 'Out of Order' &&
									!data.can_manage_maintenance
								"
								class="sm:col-span-2 text-[12px] text-on-surface-variant"
							>
								A manager approves out of order before the room leaves inventory.
							</p>
						</template>
						<label class="text-[12px] text-on-surface-variant sm:col-span-2">
							Details
							<textarea
								v-model="report.description"
								rows="2"
								class="board-input"
							></textarea>
						</label>
						<div class="flex gap-2 sm:col-span-2">
							<button
								type="submit"
								class="rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-on-primary disabled:opacity-50"
								:disabled="busy || !report.issue.trim()"
							>
								Report
							</button>
							<button
								type="button"
								class="rounded-lg border border-outline-variant px-4 py-2 text-[13px] font-semibold"
								@click="report.open = false"
							>
								Cancel
							</button>
						</div>
					</form>

					<p v-if="!data.maintenance.length" class="text-[13px] text-on-surface-variant">
						No maintenance requests this week.
					</p>
					<article
						v-for="request in data.maintenance"
						:key="request.name"
						class="rounded-xl border bg-surface-container-lowest p-3 space-y-2"
						:class="request.overdue ? 'border-error' : 'border-outline-variant'"
					>
						<div class="flex flex-wrap items-start justify-between gap-2">
							<div>
								<p class="text-[14px] font-semibold">
									{{ request.issue }}
									<span
										v-if="request.room_number"
										class="font-normal text-on-surface-variant"
									>
										· room {{ request.room_number }}</span
									>
								</p>
								<p class="text-[12px] text-on-surface-variant">
									{{ request.name }} · {{ request.severity }} ·
									{{ request.status }}
									<template v-if="request.room_impact !== 'None'">
										· {{ request.room_impact }}
										<template v-if="request.out_from">
											{{ formatNight(request.out_from) }}–{{
												formatNight(request.back_in_service_on)
											}}</template
										>
									</template>
								</p>
								<p
									v-if="
										['Open', 'Awaiting Approval', 'In Progress'].includes(
											request.status
										)
									"
									class="text-[12px]"
									:class="
										request.overdue
											? 'text-error font-semibold'
											: 'text-on-surface-variant'
									"
								>
									{{ request.overdue ? "Overdue" : "Respond by" }}
									{{ formatTimestamp(request.sla_due) }}
									<template v-if="request.assigned_to">
										· {{ request.assigned_to }}</template
									>
								</p>
								<p
									v-if="request.resolution"
									class="text-[12px] text-on-surface-variant"
								>
									Fixed: {{ request.resolution }}
									<template v-if="request.lost_room_nights">
										· {{ request.lost_room_nights }} room night(s)
										lost</template
									>
								</p>
								<p
									v-if="request.asset_repair"
									class="text-[12px] text-on-surface-variant"
								>
									Asset Repair {{ request.asset_repair }}
								</p>
							</div>
							<div class="flex flex-wrap gap-2 text-[12px] font-semibold">
								<button
									v-if="
										request.status === 'Awaiting Approval' &&
										data.can_manage_maintenance
									"
									type="button"
									class="rounded-lg bg-primary px-3 py-1.5 text-on-primary"
									:disabled="busy"
									@click="run(() => approveMaintenanceApi(request.name))"
								>
									Approve out of order
								</button>
								<button
									v-if="request.status === 'Open' && data.can_work_maintenance"
									type="button"
									class="rounded-lg border border-primary px-3 py-1.5 text-primary"
									:disabled="busy"
									@click="run(() => startMaintenanceApi(request.name))"
								>
									Start
								</button>
								<button
									v-if="
										['Open', 'In Progress'].includes(request.status) &&
										data.can_work_maintenance
									"
									type="button"
									class="rounded-lg border border-primary px-3 py-1.5 text-primary"
									:disabled="busy"
									@click="resolve(request)"
								>
									Resolve
								</button>
								<button
									v-if="
										['Open', 'Awaiting Approval', 'In Progress'].includes(
											request.status
										) && data.can_manage_maintenance
									"
									type="button"
									class="rounded-lg border border-outline-variant px-3 py-1.5"
									:disabled="busy"
									@click="cancelRequest(request)"
								>
									Cancel
								</button>
							</div>
						</div>
					</article>
				</section>
			</template>
			<p v-else-if="loading" class="text-[13px] text-on-surface-variant">Loading…</p>
		</template>
	</div>
</template>

<script setup>
import {
	computed,
	defineComponent,
	h,
	onBeforeUnmount,
	onMounted,
	reactive,
	ref,
	watch,
} from "vue";
import {
	approveMaintenanceApi,
	assignHousekeepingTaskApi,
	cancelHousekeepingTaskApi,
	cancelMaintenanceApi,
	createHousekeepingTaskApi,
	fetchHousekeepingBoardApi,
	finishHousekeepingTaskApi,
	hotelErrorMessage,
	inspectHousekeepingTaskApi,
	markDoNotDisturbApi,
	planStayoversApi,
	reportMaintenanceApi,
	resolveMaintenanceApi,
	startHousekeepingTaskApi,
	startMaintenanceApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { formatNight } from "@/utils/hotelFormat";

const CONDITION_COLORS = {
	Dirty: "#c62828",
	Pickup: "#f9a825",
	Clean: "#2e7d32",
	Inspected: "#1565c0",
};

const hotel = useHotelStore();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const loadedAt = ref("");
const tab = ref("");
const conditionFilter = ref("");
const selectedRoom = ref("");
const newTask = reactive({ type: "Touch-up", priority: "Normal", notes: "" });
const report = reactive(emptyReport());
let timer = null;

const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

const activeTasks = computed(() =>
	(data.value?.tasks || []).filter((task) => ["Open", "In Progress"].includes(task.status))
);
const myTasks = computed(() =>
	(data.value?.tasks || []).filter(
		(task) =>
			task.assigned_to && task.assigned_to === data.value?.me && task.status !== "Inspected"
	)
);
const openRequests = computed(() =>
	(data.value?.maintenance || []).filter((row) =>
		["Open", "Awaiting Approval", "In Progress"].includes(row.status)
	)
);
const tabs = computed(() => {
	const list = [];
	if (data.value?.me) {
		list.push({
			key: "mine",
			label: "My tasks",
			count: myTasks.value.filter((task) => task.status !== "Done").length,
		});
	}
	list.push({ key: "rooms", label: "Rooms", count: 0 });
	if (data.value?.can_supervise) {
		list.push({ key: "tasks", label: "Tasks", count: activeTasks.value.length });
	}
	list.push({ key: "maintenance", label: "Maintenance", count: openRequests.value.length });
	return list;
});
const summary = computed(() => {
	const rooms = data.value?.rooms || [];
	const count = (condition) =>
		rooms.filter((room) => room.housekeeping_condition === condition).length;
	return [
		...Object.entries(CONDITION_COLORS).map(([key, color]) => ({
			key,
			label: key,
			color,
			count: count(key),
		})),
		{
			key: "arrivals",
			label: "Arrivals not ready",
			count: rooms.filter((room) => room.arrival_today && !room.ready).length,
		},
	];
});
const visibleRooms = computed(() => {
	const rooms = data.value?.rooms || [];
	if (!conditionFilter.value) return rooms;
	if (conditionFilter.value === "arrivals") {
		return rooms.filter((room) => room.arrival_today && !room.ready);
	}
	return rooms.filter((room) => room.housekeeping_condition === conditionFilter.value);
});
const roomByName = computed(() =>
	Object.fromEntries((data.value?.rooms || []).map((room) => [room.name, room]))
);
const selected = computed(() => roomByName.value[selectedRoom.value] || null);
const taskGroups = computed(() => {
	const tasks = data.value?.tasks || [];
	return [
		{ label: "To inspect", tasks: tasks.filter((task) => task.status === "Done") },
		{ label: "In progress", tasks: tasks.filter((task) => task.status === "In Progress") },
		{ label: "Not started", tasks: tasks.filter((task) => task.status === "Open") },
		{ label: "Inspected", tasks: tasks.filter((task) => task.status === "Inspected") },
	];
});

function toggleFilter(key) {
	conditionFilter.value = conditionFilter.value === key ? "" : key;
	tab.value = "rooms";
}

function conditionClass(condition) {
	return (
		{
			Dirty: "border-[#c62828]/40 bg-[#c62828]/10 text-[#8e1c1c]",
			Pickup: "border-[#f9a825]/50 bg-[#f9a825]/15 text-[#7a5300]",
			Clean: "border-[#2e7d32]/40 bg-[#2e7d32]/10 text-[#1b5e20]",
			Inspected: "border-[#1565c0]/40 bg-[#1565c0]/10 text-[#0d47a1]",
		}[condition] || "border-outline-variant"
	);
}

function tasksForRoom(room) {
	return (data.value?.tasks || []).filter((task) => task.hotel_room === room);
}

function formatTimestamp(value) {
	if (!value) return "";
	return new Date(String(value).replace(" ", "T")).toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function emptyReport() {
	return {
		open: false,
		room: "",
		issue: "",
		severity: "Medium",
		roomImpact: "None",
		outFrom: "",
		backOn: "",
		description: "",
	};
}

// ------------------------------------------------------------------ commands

async function run(command, success = null) {
	busy.value = true;
	error.value = "";
	try {
		const result = await command();
		if (result?.rooms) data.value = result;
		if (result?.warnings?.length) {
			notify({
				title: "Done, with a warning",
				message: result.warnings.join(" "),
				tone: "warning",
			});
		} else if (success) {
			notify({ title: success, tone: "info" });
		}
		return true;
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
		return false;
	} finally {
		busy.value = false;
	}
}

function finish(task, roomFound = null) {
	return run(
		() => finishHousekeepingTaskApi(task.name, roomFound),
		`Room ${task.room_number} done`
	);
}

function assign(task, employee) {
	return run(() => assignHousekeepingTaskApi(task.name, employee));
}

async function inspect(task, passed) {
	if (passed) {
		return run(
			() => inspectHousekeepingTaskApi(task.name, true),
			`Room ${task.room_number} is ready`
		);
	}
	const answer = await ask({
		title: `Send room ${task.room_number} back?`,
		reasonLabel: "What needs redoing?",
		confirmLabel: "Send back",
		tone: "danger",
	});
	if (answer) run(() => inspectHousekeepingTaskApi(task.name, false, answer.reason));
}

async function cancelTask(task) {
	const answer = await ask({
		title: `Cancel the ${task.task_type.toLowerCase()} for room ${task.room_number}?`,
		reasonLabel: "Why?",
		confirmLabel: "Cancel task",
	});
	if (answer) run(() => cancelHousekeepingTaskApi(task.name, answer.reason));
}

async function addTask() {
	const done = await run(() =>
		createHousekeepingTaskApi({
			room: selected.value.name,
			taskType: newTask.type,
			priority: newTask.priority,
			notes: newTask.notes,
		})
	);
	if (done) newTask.notes = "";
}

function openReport(room) {
	Object.assign(report, emptyReport(), { open: true, room: room || "" });
	tab.value = "maintenance";
}

async function submitReport() {
	const done = await run(
		() =>
			reportMaintenanceApi({
				property: hotel.property,
				issue: report.issue.trim(),
				room: report.room,
				severity: report.severity,
				description: report.description,
				roomImpact: report.room ? report.roomImpact : "None",
				outFrom: report.outFrom,
				backInServiceOn: report.backOn,
			}),
		"Issue reported"
	);
	if (done) Object.assign(report, emptyReport());
}

async function resolve(request) {
	const answer = await ask({
		title: `Resolve "${request.issue}"?`,
		message:
			request.room_impact !== "None"
				? "The room comes back into service today, after housekeeping checks it."
				: "",
		reasonLabel: "What was done?",
		confirmLabel: "Resolve",
	});
	if (answer) run(() => resolveMaintenanceApi(request.name, answer.reason));
}

async function cancelRequest(request) {
	const answer = await ask({
		title: `Cancel "${request.issue}"?`,
		reasonLabel: "Why?",
		confirmLabel: "Cancel request",
	});
	if (answer) run(() => cancelMaintenanceApi(request.name, answer.reason));
}

// ------------------------------------------------------------------ loading

async function load({ quiet = false } = {}) {
	if (!hotel.property) return;
	if (!quiet) loading.value = true;
	try {
		data.value = await fetchHousekeepingBoardApi(hotel.property);
		if (!tab.value || !tabs.value.some((option) => option.key === tab.value)) {
			tab.value = data.value.me && !data.value.can_supervise ? "mine" : "rooms";
		}
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

function schedule() {
	clearTimeout(timer);
	const seconds = data.value?.refresh_seconds;
	if (!seconds) return;
	timer = setTimeout(() => {
		// Never refresh under someone typing or answering.
		if (busy.value || report.open || banner.value?.kind === "ask" || document.hidden) {
			schedule();
			return;
		}
		load({ quiet: true });
	}, Math.max(seconds, 15) * 1000);
}

watch(
	() => hotel.property,
	() => {
		selectedRoom.value = "";
		load();
	}
);
onMounted(async () => {
	await hotel.load();
	load();
});
onBeforeUnmount(() => clearTimeout(timer));

// ------------------------------------------------------------------ small pieces

const PRIORITY_CLASS = {
	High: "bg-error-container text-on-error-container",
	Normal: "bg-surface-container-high text-on-surface-variant",
	Low: "bg-surface-container text-on-surface-variant",
};

/** Room number, task, priority and notes: the top of a task card. */
const TaskHeading = defineComponent({
	props: { task: { type: Object, required: true }, room: { type: Object, default: null } },
	setup(props) {
		return () =>
			h("div", { class: "flex items-start justify-between gap-2" }, [
				h("div", [
					h(
						"p",
						{ class: "text-[22px] font-semibold leading-tight" },
						`Room ${props.task.room_number}`
					),
					h(
						"p",
						{ class: "text-[13px] text-on-surface-variant" },
						[
							props.task.task_type,
							props.task.status,
							props.room?.arrival_today ? "arrival today" : null,
							props.task.do_not_disturb ? "Do Not Disturb" : null,
						]
							.filter(Boolean)
							.join(" · ")
					),
					props.task.inspection_result === "Failed"
						? h(
								"p",
								{ class: "text-[12px] text-error" },
								`Redo: ${props.task.inspection_notes}`
						  )
						: null,
					props.task.notes ? h("p", { class: "text-[12px]" }, props.task.notes) : null,
				]),
				h(
					"span",
					{
						class: `rounded-full px-2 py-0.5 text-[11px] font-semibold ${
							PRIORITY_CLASS[props.task.priority] || ""
						}`,
					},
					props.task.priority
				),
			]);
	},
});

/** One task in a list, with what a supervisor (or the attendant) can do to it. */
const TaskRow = defineComponent({
	props: {
		task: { type: Object, required: true },
		data: { type: Object, required: true },
		busy: { type: Boolean, default: false },
		showRoom: { type: Boolean, default: false },
	},
	emits: ["assign", "inspect", "cancel", "start", "finish"],
	setup(props, { emit }) {
		const button = (label, onClick, extra = "") =>
			h(
				"button",
				{
					type: "button",
					class: `rounded-lg px-2.5 py-1 text-[12px] font-semibold disabled:opacity-50 ${extra}`,
					disabled: props.busy,
					onClick,
				},
				label
			);
		return () => {
			const task = props.task;
			const active = ["Open", "In Progress"].includes(task.status);
			const supervise = props.data.can_supervise;
			return h("div", { class: "flex flex-wrap items-center justify-between gap-2" }, [
				h("div", { class: "min-w-0" }, [
					h("p", { class: "font-semibold" }, [
						props.showRoom ? `Room ${task.room_number} · ` : "",
						task.task_type,
						h(
							"span",
							{
								class: `ml-2 rounded-full px-2 py-0.5 text-[10px] ${
									PRIORITY_CLASS[task.priority] || ""
								}`,
							},
							task.priority
						),
					]),
					h(
						"p",
						{ class: "text-[11px] text-on-surface-variant" },
						[
							task.status,
							task.employee_name,
							task.do_not_disturb ? "Do Not Disturb" : null,
							task.room_found ? `found ${task.room_found.toLowerCase()}` : null,
							task.inspection_result === "Failed"
								? `redo: ${task.inspection_notes}`
								: null,
							task.notes,
						]
							.filter(Boolean)
							.join(" · ")
					),
				]),
				h("div", { class: "flex flex-wrap items-center gap-1.5" }, [
					supervise && active
						? h(
								"select",
								{
									class: "rounded-lg border border-outline-variant bg-surface-container-lowest px-2 py-1 text-[12px]",
									value: task.assigned_to || "",
									disabled: props.busy,
									"aria-label": "Assign to",
									onChange: (event) => emit("assign", task, event.target.value),
								},
								[
									h("option", { value: "" }, "Unassigned"),
									...props.data.staff.map((person) =>
										h(
											"option",
											{ value: person.employee },
											`${person.employee_name}${
												person.on_shift ? "" : " (off shift)"
											} · ${person.credits}`
										)
									),
								]
						  )
						: null,
					task.status === "Open" && (supervise || task.assigned_to === props.data.me)
						? button(
								"Start",
								() => emit("start", task),
								"border border-primary text-primary"
						  )
						: null,
					task.status === "In Progress" &&
					(supervise || task.assigned_to === props.data.me)
						? button("Done", () => emit("finish", task), "bg-primary text-on-primary")
						: null,
					supervise && task.status === "Done"
						? button(
								"Pass",
								() => emit("inspect", task, true),
								"bg-primary text-on-primary"
						  )
						: null,
					supervise && task.status === "Done"
						? button(
								"Send back",
								() => emit("inspect", task, false),
								"border border-error text-error"
						  )
						: null,
					supervise && active
						? button("Cancel", () => emit("cancel", task), "text-on-surface-variant")
						: null,
				]),
			]);
		};
	},
});
</script>

<style scoped>
.board-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
.big-button {
	@apply flex min-h-[48px] items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-[14px] font-semibold disabled:opacity-50;
}
</style>
