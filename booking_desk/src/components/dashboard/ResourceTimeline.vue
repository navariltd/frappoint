<template>
	<div
		class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant overflow-hidden"
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
				<span
					v-for="status in statuses"
					:key="status.key"
					class="flex items-center gap-1 text-[12px] font-medium"
				>
					<span :class="['w-3 h-3 rounded-full', status.color]"></span>
					{{ status.label }}
				</span>
			</div>
		</div>

		<!-- Day Timeline -->
		<div
			ref="mainScrollRef"
			v-if="currentView === 'day'"
			class="overflow-x-auto scrollbar-hide"
			@scroll="onMainScroll"
		>
			<div :style="{ minWidth: minWidth }" class="w-full">
				<!-- Time Header -->
				<div class="flex border-b border-outline-variant bg-surface">
					<div
						class="w-[200px] p-3 border-r border-outline-variant font-label-md text-label-md shrink-0 sticky left-0 z-30 bg-surface shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
					>
						Provider
					</div>
					<div class="relative" :style="{ width: timelineWidth }">
						<div
							class="grid divide-x divide-outline-variant"
							:style="timeHeaderGridStyle"
						>
							<div
								v-for="time in activeTimeSlots"
								:key="time"
								class="p-3 text-center text-[12px] font-bold text-on-surface-variant"
							>
								{{ time }}
							</div>
						</div>
					</div>
				</div>

				<!-- Provider Rows -->
				<div class="divide-y divide-outline-variant">
					<div
						v-if="!hasAppointmentsForSelectedDate"
						class="h-48 flex items-center justify-center text-[13px] text-on-surface-variant"
					>
						{{ emptyDayMessage }}
					</div>
					<div
						v-else
						v-for="provider in providers"
						:key="provider.id"
						:class="['flex', providerRowClass(provider)]"
						:data-provider-id="provider.id"
					>
						<!-- Provider Info -->
						<div
							class="w-[200px] p-4 border-r border-outline-variant flex items-center gap-3 shrink-0 sticky left-0 z-20 bg-surface-container-lowest shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
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

						<!-- Timeline Slots -->
						<div class="relative h-24" :style="{ width: timelineWidth }">
							<div class="absolute inset-0 grid" :style="timeHeaderGridStyle">
								<div
									v-for="i in activeTimeSlots.length"
									:key="`grid-${provider.id}-${i}`"
									class="border-r border-outline-variant h-full"
								></div>
							</div>

							<!-- Appointment Cards -->
							<div
								v-for="appointment in getProviderAppointmentsForSelectedDate(
									provider.id
								)"
								:key="appointment.id"
								:class="[
									'group absolute top-3 rounded-lg p-2 text-[10px] shadow-sm z-10 cursor-grab active:cursor-grabbing transition-transform duration-150',
									appointmentClass(appointment),
									dragState.appointmentId === appointment.id
										? 'scale-[1.01] ring-2 ring-primary/50'
										: 'hover:scale-[1.01]',
								]"
								:style="appointmentPosition(appointment)"
								@mousedown="
									onAppointmentMouseDown($event, appointment, provider.id)
								"
								@click.stop="openDetails(appointment)"
							>
								<p class="font-bold">{{ appointment.guestName }}</p>
								<p>{{ appointment.service }}</p>
								<p v-if="appointment.delayed" class="mt-1 font-bold italic">
									{{ appointment.delayed }}
								</p>
								<span
									v-if="appointment.showTimer"
									class="absolute bottom-1 right-1 material-symbols-outlined text-[12px]"
									>timer</span
								>

								<div
									class="pointer-events-none absolute left-1/2 top-[calc(100%+6px)] z-30 hidden w-52 -translate-x-1/2 rounded-lg border border-outline-variant bg-surface p-2 text-[10px] text-on-surface shadow-lg group-hover:block"
								>
									<p class="font-bold text-[11px]">
										{{ appointment.guestName }}
									</p>
									<p class="text-on-surface-variant">
										{{ appointment.service }}
									</p>
									<p class="mt-1">Starts: {{ appointment.startTime }}</p>
									<p>Duration: {{ appointment.duration }}h</p>
									<p class="capitalize">Status: {{ appointment.status }}</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Week / Month Grid -->
		<div
			ref="mainScrollRef"
			v-else
			class="overflow-x-auto scrollbar-hide"
			@scroll="onMainScroll"
		>
			<div class="min-w-[980px]">
				<div
					class="grid border-b border-outline-variant bg-surface"
					:style="altViewGridStyle"
				>
					<div
						class="p-3 border-r border-outline-variant font-semibold text-[12px] text-on-surface sticky left-0 bg-surface z-30 shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
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

				<div class="divide-y divide-outline-variant">
					<div
						v-for="provider in providers"
						:key="`alt-${provider.id}`"
						class="grid"
						:style="altViewGridStyle"
					>
						<div
							class="p-3 border-r border-outline-variant sticky left-0 bg-surface-container-lowest z-20 shadow-[8px_0_12px_-10px_rgba(0,0,0,0.25)]"
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

		<div class="border-t border-outline-variant bg-surface px-6 py-2">
			<div
				ref="bottomScrollRef"
				class="overflow-x-auto overflow-y-hidden h-4"
				@scroll="onBottomScroll"
			>
				<div :style="{ width: scrollTrackWidth, height: '1px' }"></div>
			</div>
		</div>

		<div
			v-if="selectedAppointment"
			class="border-t border-outline-variant bg-surface px-6 py-4"
		>
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<p class="text-[11px] uppercase tracking-wide text-on-surface-variant">
						Appointment Details
					</p>
					<h3 class="text-[15px] font-semibold text-on-surface">
						{{ selectedAppointment.guestName }}
					</h3>
					<p class="text-[12px] text-on-surface-variant">
						{{ selectedAppointment.service }}
					</p>
				</div>
				<button
					type="button"
					class="material-symbols-outlined text-on-surface-variant hover:text-on-surface"
					@click="selectedAppointmentId = null"
					aria-label="Close appointment details"
				>
					close
				</button>
			</div>
			<div class="mt-3 grid grid-cols-2 gap-3 text-[12px] sm:grid-cols-4">
				<div
					class="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2"
				>
					<p class="text-on-surface-variant">Provider</p>
					<p class="font-medium text-on-surface">
						{{ providerName(selectedAppointment.providerId) }}
					</p>
				</div>
				<div
					class="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2"
				>
					<p class="text-on-surface-variant">Start</p>
					<p class="font-medium text-on-surface">
						{{ appointmentDate(selectedAppointment) }}
						{{ selectedAppointment.startTime }}
					</p>
				</div>
				<div
					class="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2"
				>
					<p class="text-on-surface-variant">Duration</p>
					<p class="font-medium text-on-surface">{{ selectedAppointment.duration }}h</p>
				</div>
				<div
					class="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2"
				>
					<p class="text-on-surface-variant">Status</p>
					<p class="font-medium capitalize text-on-surface">
						{{ selectedAppointment.status }}
					</p>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const emit = defineEmits(["appointments-updated", "view-changed", "date-changed"]);

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
const mainScrollRef = ref(null);
const bottomScrollRef = ref(null);
const syncingFromMain = ref(false);
const syncingFromBottom = ref(false);
const dragState = ref({
	appointmentId: null,
	providerId: null,
	startX: 0,
	startMinutes: 0,
	moved: false,
});

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
		if (currentView.value !== "day") {
			return;
		}

		await nextTick();
		autoScrollToRelevantTime();
	},
	{ immediate: true }
);

const slotWidth = computed(() => Math.max(90, Math.min(240, (140 * zoom.value) / 100)));

const activeTimeSlots = computed(() => {
	if (!props.showFullDay) {
		return props.timeSlots;
	}
	return Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);
});

const timelineWidth = computed(() => `${activeTimeSlots.value.length * slotWidth.value}px`);

const minWidth = computed(() => `${200 + activeTimeSlots.value.length * slotWidth.value}px`);

const altMinWidth = computed(() => Math.max(980, 200 + visibleDates.value.length * 110));

const scrollTrackWidth = computed(() => {
	if (currentView.value === "day") {
		return minWidth.value;
	}
	return `${altMinWidth.value}px`;
});

const timeHeaderGridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${activeTimeSlots.value.length}, ${slotWidth.value}px)`,
}));

const altViewGridStyle = computed(() => ({
	display: "grid",
	gridTemplateColumns: `200px repeat(${visibleDates.value.length}, minmax(110px, 1fr))`,
}));

const selectedAppointment = computed(() => {
	if (!selectedAppointmentId.value) {
		return null;
	}
	return (
		localAppointments.value.find(
			(appointment) => appointment.id === selectedAppointmentId.value
		) || null
	);
});

const timelineStartMinutes = computed(() => props.startHour * 60);
const timelineEndMinutes = computed(() => props.endHour * 60);

const appointmentDate = (appointment) => {
	return appointment.date || appointment.appointmentDate || "";
};

const getProviderAppointmentsByDate = (providerId, dateIso) => {
	return localAppointments.value
		.filter((apt) => apt.providerId === providerId && appointmentDate(apt) === dateIso)
		.sort((a, b) => parseTimeToMinutes(a.startTime) - parseTimeToMinutes(b.startTime));
};

const getProviderAppointmentsForSelectedDate = (providerId) => {
	return getProviderAppointmentsByDate(providerId, selectedDate.value);
};

const hasAppointmentsForSelectedDate = computed(() => {
	return localAppointments.value.some(
		(appointment) => appointmentDate(appointment) === selectedDate.value
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
	const durationHours = appointment.duration || 1;
	const width = Math.max(56, durationHours * slotWidth.value - 4);
	const previewOffset =
		dragState.value.appointmentId === appointment.id ? dragPreviewOffsetPx.value : 0;
	const left = (startOffsetMinutes / 60) * slotWidth.value + 2 + previewOffset;

	return {
		left: `${left}px`,
		width: `${width}px`,
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

const providerName = (providerId) => {
	const provider = props.providers.find((item) => item.id === providerId);
	return provider?.name || "Unassigned";
};

const autoScrollToRelevantTime = () => {
	if (!mainScrollRef.value || !bottomScrollRef.value) {
		return;
	}

	const selectedDayAppointments = localAppointments.value.filter(
		(appointment) => appointmentDate(appointment) === selectedDate.value
	);

	if (!selectedDayAppointments.length) {
		mainScrollRef.value.scrollLeft = 0;
		bottomScrollRef.value.scrollLeft = 0;
		return;
	}

	const earliestMinutes = selectedDayAppointments.reduce((min, appointment) => {
		const minutes = parseTimeToMinutes(appointment.startTime);
		return Math.min(min, minutes);
	}, Number.POSITIVE_INFINITY);

	const offsetMinutes = Math.max(0, earliestMinutes - timelineStartMinutes.value - 60);
	const targetScrollLeft = Math.max(0, (offsetMinutes / 60) * slotWidth.value);

	mainScrollRef.value.scrollLeft = targetScrollLeft;
	bottomScrollRef.value.scrollLeft = targetScrollLeft;
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

const onMainScroll = (event) => {
	if (syncingFromBottom.value) {
		return;
	}
	if (!bottomScrollRef.value) {
		return;
	}
	syncingFromMain.value = true;
	bottomScrollRef.value.scrollLeft = event.target.scrollLeft;
	requestAnimationFrame(() => {
		syncingFromMain.value = false;
	});
};

const onBottomScroll = (event) => {
	if (syncingFromMain.value) {
		return;
	}
	if (!mainScrollRef.value) {
		return;
	}
	syncingFromBottom.value = true;
	mainScrollRef.value.scrollLeft = event.target.scrollLeft;
	requestAnimationFrame(() => {
		syncingFromBottom.value = false;
	});
};

const openDetails = (appointment) => {
	if (Date.now() < suppressClickUntil.value) {
		return;
	}
	selectedAppointmentId.value = appointment.id;
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
		const minutePerPixel = 60 / slotWidth.value;
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
