<template>
	<div
		class="h-full bg-surface-container-lowest rounded-lg shadow-sm border border-outline-variant overflow-hidden isolate flex flex-col"
	>
		<!-- Header -->
		<div
			class="px-6 py-4 border-b border-outline-variant flex flex-wrap gap-3 justify-between items-center bg-surface-container-low"
		>
			<div>
				<h2 class="font-headline-sm text-headline-sm text-on-surface">{{ title }}</h2>
				<p class="text-[12px] text-on-surface-variant">{{ headerRangeLabel }}</p>
			</div>
			<div class="flex items-center gap-3 flex-wrap">
				<div class="inline-flex rounded-lg border border-outline-variant overflow-hidden">
					<button
						v-for="view in viewOptions"
						:key="view"
						type="button"
						:class="[
							'px-3 py-1.5 text-[12px] font-semibold capitalize transition-colors',
							currentView === view
								? 'bg-primary text-on-primary'
								: 'bg-surface text-on-surface-variant hover:text-on-surface',
						]"
						@click="setView(view)"
					>
						{{ view }}
					</button>
				</div>

				<div
					class="flex items-center gap-1 rounded-lg border border-outline-variant bg-surface px-1 py-1"
				>
					<button
						type="button"
						class="material-symbols-outlined text-[18px] text-on-surface-variant hover:text-on-surface"
						@click="shiftPeriod(-1)"
					>
						chevron_left
					</button>
					<input
						v-model="selectedDate"
						type="date"
						class="rounded-md border border-outline-variant bg-surface-container-low px-2 py-1 text-[12px] text-on-surface outline-none"
					/>
					<button
						type="button"
						class="material-symbols-outlined text-[18px] text-on-surface-variant hover:text-on-surface"
						@click="shiftPeriod(1)"
					>
						chevron_right
					</button>
				</div>

				<div v-if="currentView === 'day'" class="flex items-center gap-4 flex-wrap">
					<div
						class="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface px-2 py-1"
					>
						<button
							type="button"
							class="material-symbols-outlined text-on-surface-variant hover:text-on-surface"
							@click="setZoom(zoom - 10)"
							aria-label="Zoom out timeline"
						>
							remove
						</button>
						<span
							class="text-[11px] font-semibold text-on-surface min-w-10 text-center"
							>{{ zoom }}%</span
						>
						<button
							type="button"
							class="material-symbols-outlined text-on-surface-variant hover:text-on-surface"
							@click="setZoom(zoom + 10)"
							aria-label="Zoom in timeline"
						>
							add
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Status Legend Row -->
		<div
			v-if="statuses.length"
			class="px-6 py-2 border-b border-outline-variant flex items-center gap-x-6 gap-y-1 flex-wrap bg-surface-container-lowest"
		>
			<span
				class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider"
				>Legend</span
			>
			<span
				v-for="status in statuses"
				:key="status.key"
				class="flex items-center gap-1.5 text-[11px] font-medium text-on-surface-variant"
			>
				<span :class="['w-2.5 h-2.5 rounded-full flex-shrink-0', status.color]"></span>
				{{ status.label }}
			</span>
		</div>

		<!-- Day Timeline -->
		<div
			v-if="currentView === 'day'"
			class="flex-1 min-h-0 overflow-hidden bg-surface-container-lowest relative z-0"
		>
			<div class="w-full h-full bg-surface-container-lowest flex flex-col overflow-hidden">
				<!-- Time Header -->
				<div
					class="flex border-b border-outline-variant bg-surface-container-lowest shrink-0"
				>
					<div
						class="p-3 border-r border-outline-variant font-label-md text-label-md shrink-0 sticky left-0 z-40 bg-surface-container-lowest shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
						:style="providerColumnStyle"
					>
						Provider
					</div>
					<div
						ref="dayHeaderScrollRef"
						class="min-w-0 flex-1 overflow-x-auto overflow-y-hidden scrollbar-hide"
						@scroll="onDayHeaderScroll"
					>
						<div
							class="relative bg-surface-container-lowest"
							:style="timelineGridStyle"
						>
							<div class="grid divide-x divide-outline" :style="timeHeaderGridStyle">
								<div
									v-for="time in activeTimeSlots"
									:key="time"
									class="p-3 text-center text-[12px] font-bold text-on-surface-variant whitespace-nowrap"
								>
									{{ time }}
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Provider Rows -->
				<div
					class="flex-1 min-h-0 bg-surface-container-lowest overflow-y-auto overflow-x-hidden"
				>
					<div
						v-if="!hasAppointmentsForSelectedDate"
						class="h-48 flex items-center justify-center text-[13px] text-on-surface-variant"
					>
						{{ emptyDayMessage }}
					</div>
					<div v-else class="flex min-w-0">
						<div class="shrink-0" :style="providerColumnStyle">
							<div
								v-for="provider in providers"
								:key="`provider-col-${provider.id}`"
								:class="[
									'p-4 border-r border-b border-outline-variant flex items-center gap-3 bg-surface-container-lowest sticky left-0 z-30 shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]',
									providerRowClass(provider),
									providerRowsScrollable ? 'h-24 shrink-0' : 'min-h-[6rem]',
								]"
							>
								<div
									class="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center font-bold text-[10px]"
								>
									{{ provider.initials }}
								</div>
								<div>
									<p class="font-label-sm text-label-sm leading-tight">
										{{ provider.name }}
									</p>
									<p
										class="text-[10px]"
										:class="
											provider.overloaded
												? 'text-error font-bold flex items-center gap-0.5'
												: 'text-on-surface-variant'
										"
									>
										<span
											v-if="provider.overloaded"
											class="material-symbols-outlined text-[12px]"
											>bolt</span
										>
										{{ provider.designation }}
									</p>
								</div>
							</div>
						</div>
						<div
							ref="dayBodyScrollRef"
							class="min-w-0 flex-1 overflow-x-auto overflow-y-hidden scrollbar-hide"
							@scroll="onDayBodyScroll"
						>
							<div :style="timelineGridStyle">
								<div
									v-for="provider in providers"
									:key="provider.id"
									class="relative border-b border-outline-variant bg-surface-container-lowest"
									:class="providerRowsScrollable ? 'h-24' : 'min-h-[6rem]'"
									:data-provider-id="provider.id"
								>
									<div
										class="absolute inset-0 grid"
										:style="timeHeaderGridStyle"
									>
										<div
											v-for="i in activeTimeSlots.length"
											:key="`day-grid-${provider.id}-${i}`"
											class="border-r border-outline-variant h-full"
										></div>
									</div>
									<div
										v-if="
											!getProviderAppointmentsForSelectedDate(provider.id)
												.length
										"
										class="absolute left-2 top-2 z-10 text-[10px] text-on-surface-variant"
									>
										No appointments
									</div>
									<div
										v-for="(
											appointment, appointmentIndex
										) in getProviderAppointmentsForSelectedDate(provider.id)"
										:key="appointment.id"
										:class="[
											'group absolute rounded-lg p-2 text-[10px] shadow-sm z-10 cursor-grab active:cursor-grabbing transition-transform duration-150',
											appointmentClass(appointment),
											dragState.appointmentId === appointment.id
												? 'scale-[1.01] ring-2 ring-primary/50'
												: 'hover:scale-[1.01]',
										]"
										:style="
											appointmentCardStyle(appointment, appointmentIndex)
										"
										@mousedown="
											onAppointmentMouseDown(
												$event,
												appointment,
												provider.id
											)
										"
										@click.stop="openDetails(appointment)"
									>
										<p class="font-bold">{{ appointment.guestName }}</p>
										<p>{{ appointment.service }}</p>
										<p
											v-if="appointment.delayed"
											class="mt-1 font-bold italic"
										>
											{{ appointment.delayed }}
										</p>
										<span
											v-if="appointment.showTimer"
											class="absolute bottom-1 right-1 material-symbols-outlined text-[12px]"
											>timer</span
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Week / Month Grid -->
		<div
			v-else
			class="flex-1 min-h-0 overflow-hidden bg-surface-container-lowest relative z-0"
		>
			<div class="h-full overflow-x-hidden overflow-y-hidden">
				<div class="h-full flex flex-col overflow-x-auto overflow-y-auto">
					<div
						class="grid border-b border-outline-variant bg-surface-container-lowest"
						:style="altViewGridStyle"
					>
						<div
							class="p-3 border-r border-outline-variant font-semibold text-[12px] text-on-surface sticky left-0 bg-surface-container-lowest z-40 shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
							:style="providerColumnStyle"
						>
							Provider
						</div>
						<div
							v-for="day in visibleDates"
							:key="day.iso"
							class="p-3 border-r border-outline-variant text-center text-[11px] text-on-surface-variant"
						>
							<p class="font-semibold text-on-surface">{{ day.shortLabel }}</p>
							<p>{{ day.dayLabel }}</p>
						</div>
					</div>

					<div
						class="flex-1 min-h-0 divide-y divide-outline-variant bg-surface-container-lowest"
					>
						<div
							v-for="provider in providers"
							:key="`alt-${provider.id}`"
							class="grid"
							:style="altViewGridStyle"
						>
							<div
								class="p-3 border-r border-outline-variant sticky left-0 bg-surface-container-lowest z-30 shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
								:style="providerColumnStyle"
							>
								<p class="text-[12px] font-semibold text-on-surface">
									{{ provider.name }}
								</p>
								<p class="text-[10px] text-on-surface-variant">
									{{ provider.designation }}
								</p>
							</div>
							<div
								v-for="day in visibleDates"
								:key="`${provider.id}-${day.iso}`"
								class="min-h-24 border-r border-outline-variant p-2"
							>
								<div class="space-y-1">
									<button
										v-for="appointment in getProviderAppointmentsByDate(
											provider.id,
											day.iso
										).slice(0, 3)"
										:key="appointment.id"
										type="button"
										:class="[
											'w-full rounded-md px-2 py-1 text-left text-[10px] font-medium',
											appointmentClass(appointment),
										]"
										@click="openDetails(appointment)"
									>
										{{ appointment.startTime }} {{ appointment.guestName }}
									</button>
									<p
										v-if="
											getProviderAppointmentsByDate(provider.id, day.iso)
												.length > 3
										"
										class="text-[10px] text-on-surface-variant"
									>
										+{{
											getProviderAppointmentsByDate(provider.id, day.iso)
												.length - 3
										}}
										more
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const emit = defineEmits([
	"appointments-updated",
	"view-changed",
	"date-changed",
	"appointment-selected",
]);

function dateToIso(date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
		date.getDate()
	).padStart(2, "0")}`;
}

function isoToDate(iso) {
	const [year, month, day] = iso.split("-").map(Number);
	return new Date(year, month - 1, day);
}

function addDays(date, days) {
	const next = new Date(date);
	next.setDate(next.getDate() + days);
	return next;
}

function startOfWeek(date) {
	const d = new Date(date);
	const day = d.getDay();
	const diff = day === 0 ? -6 : 1 - day;
	return addDays(d, diff);
}

function buildDayMeta(date) {
	return {
		iso: dateToIso(date),
		shortLabel: date.toLocaleDateString(undefined, { weekday: "short" }),
		dayLabel: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
	};
}

function formatDateLong(date) {
	return date.toLocaleDateString(undefined, {
		weekday: "long",
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}

const props = defineProps({
	title: {
		type: String,
		default: "Resource Timeline",
	},
	providers: {
		type: Array,
		required: true,
		// [{id, name, initials, designation, overloaded}]
	},
	appointments: {
		type: Array,
		required: true,
		// [{id, providerId, guestName, service, startTime, duration, status, delayed, showTimer}]
	},
	timeSlots: {
		type: Array,
		default: () => ["09:00", "10:00", "11:00", "12:00", "13:00"],
	},
	startHour: {
		type: Number,
		default: 0,
	},
	endHour: {
		type: Number,
		default: 24,
	},
	defaultView: {
		type: String,
		default: "day",
	},
	selectedDateValue: {
		type: String,
		default: "",
	},
	showFullDay: {
		type: Boolean,
		default: true,
	},
	statuses: {
		type: Array,
		default: () => [
			{ key: "Open", label: "Open", color: "bg-primary-container" },
			{ key: "Checked-In", label: "Checked-In", color: "bg-secondary-fixed" },
			{ key: "Ongoing", label: "Ongoing", color: "bg-primary" },
		],
	},
});

const viewOptions = ["day", "week", "month"];

const zoom = ref(100);
const localAppointments = ref([]);
const selectedAppointmentId = ref(null);
const currentView = ref(viewOptions.includes(props.defaultView) ? props.defaultView : "day");
const selectedDate = ref(props.selectedDateValue || dateToIso(new Date()));
const suppressClickUntil = ref(0);
const dragState = ref({
	appointmentId: null,
	providerId: null,
	startX: 0,
	startMinutes: 0,
	timelineWidthPx: 1,
	moved: false,
});

const dayHeaderScrollRef = ref(null);
const dayBodyScrollRef = ref(null);
const isSyncingDayHorizontal = ref(false);

watch(
	() => props.appointments,
	(nextAppointments) => {
		localAppointments.value = nextAppointments.map((appointment) => ({ ...appointment }));
	},
	{ immediate: true, deep: true }
);

watch(selectedDate, (value) => {
	emit("date-changed", value);
});

watch(currentView, (value) => {
	emit("view-changed", value);
});

watch(
	() => [currentView.value, selectedDate.value, localAppointments.value.length],
	async () => {
		await nextTick();
	},
	{ immediate: true }
);

const providerColumnWidthPx = 176;

const providerColumnStyle = computed(() => ({
	width: `${providerColumnWidthPx}px`,
	minWidth: `${providerColumnWidthPx}px`,
	maxWidth: `${providerColumnWidthPx}px`,
}));

const slotWidth = computed(() => Math.max(120, Math.min(260, (160 * zoom.value) / 100)));

const activeTimeSlots = computed(() => {
	if (!props.showFullDay) {
		return props.timeSlots;
	}
	return Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);
});

const timelineGridWidthPx = computed(() => activeTimeSlots.value.length * slotWidth.value);

const timelineGridStyle = computed(() => ({
	width: `${timelineGridWidthPx.value}px`,
	minWidth: `${timelineGridWidthPx.value}px`,
}));

const dayTrackStyle = computed(() => ({
	minWidth: `${providerColumnWidthPx + timelineGridWidthPx.value}px`,
}));

const timeHeaderGridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${activeTimeSlots.value.length}, ${slotWidth.value}px)`,
}));

const altSlotWidthPx = computed(() => (currentView.value === "month" ? 132 : 156));

const altViewGridStyle = computed(() => ({
	display: "grid",
	gridTemplateColumns: `${providerColumnWidthPx}px repeat(${visibleDates.value.length}, ${altSlotWidthPx.value}px)`,
	minWidth: `${providerColumnWidthPx + visibleDates.value.length * altSlotWidthPx.value}px`,
}));

const providerRowsScrollable = computed(() => props.providers.length > 6);

const timelineStartMinutes = computed(() => props.startHour * 60);
const timelineEndMinutes = computed(() => props.endHour * 60);

const normalizeDateKey = (value) => {
	if (!value) {
		return "";
	}

	const raw = String(value).trim();
	const datePart = raw.split(" ")[0].split("T")[0];
	if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
		return datePart;
	}

	const normalized = datePart.replace(/\//g, "-");
	if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
		return normalized;
	}

	const parsed = new Date(raw);
	if (!Number.isNaN(parsed.getTime())) {
		return dateToIso(parsed);
	}

	return normalized;
};

const appointmentDate = (appointment) => {
	return normalizeDateKey(appointment.date || appointment.appointmentDate || "");
};

const getProviderAppointmentsByDate = (providerId, dateIso) => {
	const normalizedDateIso = normalizeDateKey(dateIso);
	return localAppointments.value
		.filter(
			(apt) => apt.providerId === providerId && appointmentDate(apt) === normalizedDateIso
		)
		.sort((a, b) => parseTimeToMinutes(a.startTime) - parseTimeToMinutes(b.startTime));
};

const getProviderAppointmentsForSelectedDate = (providerId) => {
	return getProviderAppointmentsByDate(providerId, selectedDate.value);
};

const hasAppointmentsForSelectedDate = computed(() => {
	const normalizedSelectedDate = normalizeDateKey(selectedDate.value);
	return localAppointments.value.some(
		(appointment) => appointmentDate(appointment) === normalizedSelectedDate
	);
});

const emptyDayMessage = computed(() => {
	const today = dateToIso(new Date());
	if (selectedDate.value === today) {
		return "No appointments scheduled for today";
	}
	return "No appointments scheduled for selected day";
});

const visibleDates = computed(() => {
	const baseDate = isoToDate(selectedDate.value);
	if (currentView.value === "day") {
		return [buildDayMeta(baseDate)];
	}

	if (currentView.value === "week") {
		const weekStart = startOfWeek(baseDate);
		return Array.from({ length: 7 }, (_, index) => {
			const date = addDays(weekStart, index);
			return buildDayMeta(date);
		});
	}

	const monthStart = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
	const daysInMonth = new Date(baseDate.getFullYear(), baseDate.getMonth() + 1, 0).getDate();
	return Array.from({ length: daysInMonth }, (_, index) => {
		const date = addDays(monthStart, index);
		return buildDayMeta(date);
	});
});

const headerRangeLabel = computed(() => {
	if (currentView.value === "day") {
		return `Day View - ${formatDateLong(isoToDate(selectedDate.value))}`;
	}
	if (currentView.value === "week") {
		const start = visibleDates.value[0];
		const end = visibleDates.value[visibleDates.value.length - 1];
		return `${start.dayLabel} to ${end.dayLabel}`;
	}
	const monthDate = isoToDate(selectedDate.value);
	return monthDate.toLocaleDateString(undefined, { month: "long", year: "numeric" });
});

const appointmentPosition = (appointment) => {
	const startOffsetMinutes = getTimeOffsetMinutes(appointment.startTime);
	const durationMinutes = getAppointmentDurationMinutes(appointment);
	const totalTimelineMinutes = Math.max(
		1,
		timelineEndMinutes.value - timelineStartMinutes.value
	);
	const widthPercent = Math.max(0.5, (durationMinutes * 100) / totalTimelineMinutes);
	const previewOffset =
		dragState.value.appointmentId === appointment.id ? dragPreviewOffsetPx.value : 0;
	const leftPercent = (startOffsetMinutes * 100) / totalTimelineMinutes;
	const previewOffsetPercent =
		dragState.value.appointmentId === appointment.id
			? (previewOffset * 100) / Math.max(1, dragState.value.timelineWidthPx)
			: 0;

	return {
		left: `${Math.max(0, Math.min(100, leftPercent + previewOffsetPercent))}%`,
		width: `${Math.max(0.5, Math.min(100, widthPercent))}%`,
	};
};

const getAppointmentDurationMinutes = (appointment) => {
	const rawDuration = Number(appointment?.duration);
	if (Number.isFinite(rawDuration) && rawDuration > 0) {
		// Most records store duration in hours, but some payloads provide minutes.
		if (rawDuration <= 12) {
			return rawDuration * 60;
		}
		if (rawDuration <= 24 * 60) {
			return rawDuration;
		}
	}

	const startMinutes = parseTimeToMinutes(appointment?.startTime);
	const endMinutes = parseTimeToMinutes(appointment?.endTime);
	if (
		Number.isFinite(startMinutes) &&
		Number.isFinite(endMinutes) &&
		endMinutes > startMinutes
	) {
		return endMinutes - startMinutes;
	}

	return 60;
};

const appointmentCardStyle = (appointment, appointmentIndex) => {
	const position = appointmentPosition(appointment);
	const laneHeightPx = 24;
	const laneTopPx = 6 + appointmentIndex * laneHeightPx;

	return {
		...position,
		top: `${laneTopPx}px`,
	};
};

const dragPreviewOffsetPx = computed(() => {
	if (!dragState.value.appointmentId) {
		return 0;
	}
	return dragCurrentX.value - dragState.value.startX;
});

const dragCurrentX = ref(0);

const parseTimeToMinutes = (time) => {
	if (!time) {
		return timelineStartMinutes.value;
	}

	const raw = String(time).trim().toLowerCase();
	const ampmMatch = raw.match(/^(\d{1,2})(?::(\d{1,2}))?(?::\d{1,2})?\s*(am|pm)$/i);
	if (ampmMatch) {
		const hour12 = Number(ampmMatch[1]);
		const minute = Number(ampmMatch[2] || 0);
		const suffix = ampmMatch[3].toLowerCase();
		let hour24 = hour12 % 12;
		if (suffix === "pm") {
			hour24 += 12;
		}
		return hour24 * 60 + minute;
	}

	const hmsMatch = raw.match(/^(\d{1,2})(?::(\d{1,2}))?(?::\d{1,2})?/);
	if (hmsMatch) {
		const hours = Number(hmsMatch[1]);
		const minutes = Number(hmsMatch[2] || 0);
		return hours * 60 + minutes;
	}

	return timelineStartMinutes.value;
};

const formatMinutesToTime = (minutes) => {
	const hours = Math.floor(minutes / 60);
	const mins = minutes % 60;
	return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const getTimeOffsetMinutes = (time) => {
	return parseTimeToMinutes(time) - timelineStartMinutes.value;
};

const appointmentClass = (appointment) => {
	const status = String(appointment.status || "")
		.trim()
		.toLowerCase();

	const classesByStatus = {
		open: "bg-primary-container text-on-primary-container border border-white/20",
		"pending payment":
			"bg-tertiary-container text-on-tertiary-container border border-white/20",
		confirmed: "bg-secondary-fixed text-on-secondary-fixed-variant border-0",
		"checked-in": "bg-secondary-fixed text-on-secondary-fixed-variant border-0",
		ongoing: "bg-primary text-on-primary border-0",
		rescheduled: "bg-error-container text-on-error-container border border-error/20",
		completed: "bg-secondary-container text-on-secondary-container border border-secondary/20",
		cancelled:
			"bg-surface-variant text-on-surface-variant opacity-70 border border-dashed border-outline",
		closed: "bg-surface-variant text-on-surface-variant opacity-70 border border-dashed border-outline",
		"no show": "bg-error text-on-error border-0",
	};

	return (
		classesByStatus[status] ||
		"bg-primary-container text-on-primary-container border border-white/20"
	);
};

const providerRowClass = (provider) => {
	return provider.overloaded ? "bg-error-container/10" : "";
};

const syncHorizontalScroll = (sourceEl, targetEl, syncFlag) => {
	if (!sourceEl || !targetEl || syncFlag.value) {
		return;
	}
	syncFlag.value = true;
	targetEl.scrollLeft = sourceEl.scrollLeft;
	requestAnimationFrame(() => {
		syncFlag.value = false;
	});
};

const onDayHeaderScroll = () => {
	syncHorizontalScroll(dayHeaderScrollRef.value, dayBodyScrollRef.value, isSyncingDayHorizontal);
};

const onDayBodyScroll = () => {
	syncHorizontalScroll(dayBodyScrollRef.value, dayHeaderScrollRef.value, isSyncingDayHorizontal);
};

const setZoom = (value) => {
	zoom.value = Math.max(70, Math.min(160, value));
};

const setView = (view) => {
	if (viewOptions.includes(view)) {
		currentView.value = view;
	}
};

const shiftPeriod = (direction) => {
	const base = isoToDate(selectedDate.value);
	if (currentView.value === "day") {
		selectedDate.value = dateToIso(addDays(base, direction));
		return;
	}
	if (currentView.value === "week") {
		selectedDate.value = dateToIso(addDays(base, direction * 7));
		return;
	}
	selectedDate.value = dateToIso(
		new Date(base.getFullYear(), base.getMonth() + direction, base.getDate())
	);
};

const openDetails = (appointment) => {
	if (Date.now() < suppressClickUntil.value) {
		return;
	}
	selectedAppointmentId.value = appointment.id;
	emit("appointment-selected", { ...appointment });
};

const onAppointmentMouseDown = (event, appointment, providerId) => {
	if (currentView.value !== "day") {
		return;
	}
	dragState.value = {
		appointmentId: appointment.id,
		providerId,
		startX: event.clientX,
		startMinutes: parseTimeToMinutes(appointment.startTime),
		timelineWidthPx:
			event.currentTarget?.parentElement?.clientWidth ||
			event.currentTarget?.closest("[data-provider-id]")?.clientWidth ||
			1,
		moved: false,
	};
	dragCurrentX.value = event.clientX;
	window.addEventListener("mousemove", onMouseMove);
	window.addEventListener("mouseup", onMouseUp);
};

const onMouseMove = (event) => {
	if (!dragState.value.appointmentId) {
		return;
	}
	dragCurrentX.value = event.clientX;
	if (Math.abs(dragCurrentX.value - dragState.value.startX) > 5) {
		dragState.value.moved = true;
	}
};

const onMouseUp = () => {
	if (!dragState.value.appointmentId) {
		removeDragListeners();
		return;
	}

	const appointment = localAppointments.value.find(
		(item) => item.id === dragState.value.appointmentId
	);
	if (!appointment) {
		resetDragState();
		return;
	}

	if (dragState.value.moved) {
		const totalTimelineMinutes = Math.max(
			1,
			timelineEndMinutes.value - timelineStartMinutes.value
		);
		const minutePerPixel = totalTimelineMinutes / Math.max(1, dragState.value.timelineWidthPx);
		const movedMinutes = (dragCurrentX.value - dragState.value.startX) * minutePerPixel;
		const rawStart = dragState.value.startMinutes + movedMinutes;
		const snappedStart = Math.round(rawStart / 15) * 15;
		const appointmentDurationMinutes = Math.round((appointment.duration || 1) * 60);
		const clampedStart = Math.max(
			timelineStartMinutes.value,
			Math.min(timelineEndMinutes.value - appointmentDurationMinutes, snappedStart)
		);

		appointment.startTime = formatMinutesToTime(clampedStart);
		appointment.date = selectedDate.value;
		emit(
			"appointments-updated",
			localAppointments.value.map((item) => ({ ...item }))
		);
		suppressClickUntil.value = Date.now() + 250;
	}

	resetDragState();
};

const removeDragListeners = () => {
	window.removeEventListener("mousemove", onMouseMove);
	window.removeEventListener("mouseup", onMouseUp);
};

const resetDragState = () => {
	removeDragListeners();
	dragState.value = {
		appointmentId: null,
		providerId: null,
		startX: 0,
		startMinutes: 0,
		timelineWidthPx: 1,
		moved: false,
	};
	dragCurrentX.value = 0;
};

onBeforeUnmount(() => {
	removeDragListeners();
});
</script>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
	display: none;
}
</style>
