<template>
	<section class="space-y-4">
		<div
			v-if="error"
			class="rounded-lg border border-error-container bg-error-container/30 px-4 py-3"
		>
			<p class="text-[12px] text-on-surface">{{ error }}</p>
			<button class="mt-2 text-[12px] font-semibold text-primary" @click="retry">
				Retry
			</button>
		</div>

		<CalendarToolbar
			:activeView="activeView"
			:rangeLabel="rangeLabel"
			:filters="filters"
			:providerOptions="providerOptions"
			:resourceOptions="resourceOptions"
			:statusOptions="statusOptions"
			@prev="goPrev"
			@next="goNext"
			@today="goToday"
			@changeView="setView"
			@update:provider="onProviderChange"
			@update:resource="onResourceChange"
			@update:status="onStatusChange"
		/>

		<CalendarLoadingState v-if="isLoading" />
		<CalendarEmptyState v-else-if="!hasEvents" @refresh="retry" />

		<div
			v-else-if="activeView !== 'month'"
			class="rounded-xl border border-outline-variant/30 bg-surface-container-lowest overflow-auto"
		>
			<div
				class="grid sticky top-0 z-10 bg-surface-container-low border-b border-outline-variant/20"
				:style="{ gridTemplateColumns: gridTemplateColumns }"
			>
				<div class="h-12 border-r border-outline-variant/20"></div>
				<div
					v-for="date in visibleDates"
					:key="date"
					class="h-12 border-r border-outline-variant/20 flex flex-col items-center justify-center"
				>
					<p class="text-[10px] uppercase font-bold text-outline">
						{{ weekdayShort(date) }}
					</p>
					<p class="text-[14px] font-semibold text-on-surface">{{ dayNumber(date) }}</p>
				</div>
			</div>
			<div class="grid relative" :style="{ gridTemplateColumns: gridTemplateColumns }">
				<div class="border-r border-outline-variant/20 bg-surface-container-low">
					<div
						v-for="hour in hours"
						:key="hour"
						class="h-[72px] border-b border-outline-variant/20 px-2 py-1 text-[10px] text-outline font-semibold"
					>
						{{ hourLabel(hour) }}
					</div>
				</div>
				<div
					v-for="date in visibleDates"
					:key="`${date}-col`"
					class="relative border-r border-outline-variant/10 min-h-[936px]"
				>
					<div
						v-for="hour in hours"
						:key="`${date}-${hour}`"
						class="h-[72px] border-b border-outline-variant/15"
					></div>
					<div class="absolute inset-0 pointer-events-none">
						<div
							v-for="event in eventsByDate[date] || []"
							:key="event.id"
							class="absolute left-1 right-1 pointer-events-auto z-10 hover:z-[999] focus-within:z-[999]"
							:style="eventStyle(event)"
						>
							<CalendarEventCard :event="event" @select="onSelectEvent" />
						</div>
					</div>
				</div>
			</div>
		</div>

		<div
			v-else
			class="rounded-xl border border-outline-variant/30 bg-surface-container-lowest overflow-hidden"
		>
			<div
				class="grid grid-cols-7 bg-surface-container-low border-b border-outline-variant/20"
			>
				<div
					v-for="label in weekdayLabels"
					:key="label"
					class="px-2 py-2 text-[11px] font-semibold text-outline text-center"
				>
					{{ label }}
				</div>
			</div>
			<div class="grid grid-cols-7">
				<div
					v-for="date in monthGridDates"
					:key="date"
					class="min-h-[130px] border-r border-b border-outline-variant/15 p-2"
					:class="{ 'bg-surface-container-low/50': !isCurrentMonth(date) }"
				>
					<p class="text-[11px] font-semibold text-on-surface mb-1">
						{{ dayNumber(date) }}
					</p>
					<div class="space-y-1">
						<button
							v-for="event in (eventsByDate[date] || []).slice(0, 3)"
							:key="event.id"
							class="w-full rounded px-1.5 py-1 text-left text-[10px] bg-primary-container/30 text-on-surface truncate hover:bg-primary-container/50"
							@click="onSelectEvent(event)"
						>
							{{ event.startTime }} {{ event.service }}
						</button>
					</div>
				</div>
			</div>
		</div>

		<CalendarAppointmentDrawer
			:open="Boolean(selectedEvent)"
			:event="selectedEvent"
			:busy="isActionLoading"
			@close="clearSelectedEvent"
			@openFull="openFullAppointment"
			@action="runAction"
		/>
	</section>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import CalendarAppointmentDrawer from "@/components/calendar/CalendarAppointmentDrawer.vue";
import CalendarEmptyState from "@/components/calendar/CalendarEmptyState.vue";
import CalendarEventCard from "@/components/calendar/CalendarEventCard.vue";
import CalendarLoadingState from "@/components/calendar/CalendarLoadingState.vue";
import CalendarToolbar from "@/components/calendar/CalendarToolbar.vue";
import { useCalendarWorkspace } from "@/composables/bookings/useCalendarWorkspace";

const router = useRouter();

const {
	events,
	selectedEvent,
	activeView,
	anchorDate,
	filters,
	isLoading,
	isActionLoading,
	error,
	providerOptions,
	resourceOptions,
	statusOptions,
	hasEvents,
	setView,
	goToday,
	goPrev,
	goNext,
	selectEvent,
	clearSelectedEvent,
	updateFilters,
	performAction,
	retry,
} = useCalendarWorkspace();

const DAY_START_HOUR = 8;
const DAY_END_HOUR = 20;
const PIXELS_PER_MINUTE = 1.2;
const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const hours = computed(() =>
	Array.from({ length: DAY_END_HOUR - DAY_START_HOUR + 1 }, (_, idx) => DAY_START_HOUR + idx)
);

function parseIsoDate(value) {
	const date = new Date(`${value}T12:00:00`);
	return Number.isNaN(date.getTime()) ? new Date() : date;
}

function isoDate(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function weekStart(date) {
	const result = new Date(date);
	const day = result.getDay();
	const diff = day === 0 ? -6 : 1 - day;
	result.setDate(result.getDate() + diff);
	return result;
}

const visibleDates = computed(() => {
	const anchor = parseIsoDate(anchorDate.value);
	if (activeView.value === "day") {
		return [isoDate(anchor)];
	}
	const start = weekStart(anchor);
	return Array.from({ length: 7 }, (_, idx) => {
		const date = new Date(start);
		date.setDate(start.getDate() + idx);
		return isoDate(date);
	});
});

const gridTemplateColumns = computed(
	() => `72px repeat(${visibleDates.value.length}, minmax(160px, 1fr))`
);

const eventsByDate = computed(() => {
	return events.value.reduce((acc, event) => {
		const key = event.date;
		if (!key) {
			return acc;
		}
		if (!acc[key]) {
			acc[key] = [];
		}
		acc[key].push(event);
		return acc;
	}, {});
});

const monthGridDates = computed(() => {
	const anchor = parseIsoDate(anchorDate.value);
	const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
	const monthEnd = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
	const start = weekStart(monthStart);
	const end = new Date(monthEnd);
	end.setDate(monthEnd.getDate() + (7 - (monthEnd.getDay() || 7)));

	const dates = [];
	const cursor = new Date(start);
	while (cursor <= end) {
		dates.push(isoDate(cursor));
		cursor.setDate(cursor.getDate() + 1);
	}
	return dates;
});

const rangeLabel = computed(() => {
	const anchor = parseIsoDate(anchorDate.value);
	if (activeView.value === "day") {
		return anchor.toLocaleDateString(undefined, {
			weekday: "short",
			month: "short",
			day: "numeric",
		});
	}
	if (activeView.value === "month") {
		return anchor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
	}
	const start = weekStart(anchor);
	const end = new Date(start);
	end.setDate(start.getDate() + 6);
	return `${start.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
	})} - ${end.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		year: "numeric",
	})}`;
});

function toMinutes(date) {
	return date.getHours() * 60 + date.getMinutes();
}

function eventStyle(event) {
	if (!event.startAt || !event.endAt) {
		return { top: "0px", height: "32px" };
	}
	const dayStartMinutes = DAY_START_HOUR * 60;
	const eventStart = Math.max(toMinutes(new Date(event.startAt)), dayStartMinutes);
	const eventEnd = Math.min(toMinutes(new Date(event.endAt)), DAY_END_HOUR * 60);
	const duration = Math.max(eventEnd - eventStart, 30);
	return {
		top: `${(eventStart - dayStartMinutes) * PIXELS_PER_MINUTE}px`,
		height: `${Math.max(duration * PIXELS_PER_MINUTE, 34)}px`,
	};
}

function weekdayShort(date) {
	return parseIsoDate(date).toLocaleDateString(undefined, { weekday: "short" });
}

function dayNumber(date) {
	return parseIsoDate(date).toLocaleDateString(undefined, { day: "numeric" });
}

function isCurrentMonth(date) {
	const anchor = parseIsoDate(anchorDate.value);
	const value = parseIsoDate(date);
	return value.getMonth() === anchor.getMonth() && value.getFullYear() === anchor.getFullYear();
}

function hourLabel(hour) {
	const suffix = hour >= 12 ? "PM" : "AM";
	const display = hour > 12 ? hour - 12 : hour;
	return `${display}:00 ${suffix}`;
}

function onSelectEvent(event) {
	selectEvent(event);
}

function openFullAppointment(event) {
	router.push({
		name: "AppointmentDetails",
		params: { appointmentId: event.appointmentId },
		query: { source: "calendar" },
	});
}

function runAction(action) {
	performAction(action);
}

function onProviderChange(value) {
	updateFilters({ provider: value || "" }, { debounceMs: 0 });
}

function onResourceChange(value) {
	updateFilters({ resource: value || "" }, { debounceMs: 0 });
}

function onStatusChange(value) {
	updateFilters({ statuses: value ? [value] : [] }, { debounceMs: 0 });
}
</script>
