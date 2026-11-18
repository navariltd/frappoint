<template>
	<section class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<div class="flex items-start justify-between gap-3">
			<div>
				<h3 class="text-[14px] font-semibold text-on-surface flex items-center gap-2">
					<span class="material-symbols-outlined text-[18px] text-primary">hotel</span>
					Charge to a hotel room
				</h3>
				<p class="text-[12px] text-on-surface-variant mt-0.5">
					For guests staying at the hotel. Each service is added to the guest's folio
					when it is completed, and settled when they check out. No payment is taken
					here.
				</p>
			</div>
			<button
				v-if="collapsible"
				type="button"
				class="text-[12px] font-semibold text-primary whitespace-nowrap"
				@click="open = !open"
			>
				{{ open ? "Hide" : "Choose a room" }}
			</button>
		</div>

		<template v-if="open">
			<label class="block text-[12px] text-on-surface-variant">
				Find the stay
				<input
					v-model="query"
					type="search"
					placeholder="Guest name, room number or stay"
					class="mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30"
					@input="searchSoon"
				/>
			</label>

			<p v-if="searching" class="text-[12px] text-on-surface-variant">Searching…</p>
			<p
				v-else-if="query && !stays.length && !selected"
				class="text-[12px] text-on-surface-variant"
			>
				No confirmed or in-house stay matches "{{ query }}".
			</p>

			<ul v-if="!selected && stays.length" class="space-y-1.5 max-h-56 overflow-y-auto">
				<li v-for="stay in stays" :key="stay.name">
					<button
						type="button"
						class="w-full text-left rounded-lg border border-outline-variant px-3 py-2 hover:bg-surface-container-high transition-colors"
						@click="choose(stay)"
					>
						<div class="flex items-center justify-between gap-2">
							<span class="text-[13px] font-semibold text-on-surface">
								{{ stay.guests[0]?.guestName || stay.name }}
							</span>
							<span class="text-[11px] text-on-surface-variant">
								{{ stay.room ? `Room ${stay.room}` : "No room yet" }} ·
								{{ stay.status }}
							</span>
						</div>
						<p class="text-[11px] text-on-surface-variant">
							{{ stay.name }} · {{ formatDate(stay.arrival) }} –
							{{ formatDate(stay.departure) }}
						</p>
					</button>
				</li>
			</ul>

			<div v-if="selected" class="space-y-3">
				<div
					class="flex items-center justify-between gap-2 rounded-lg bg-primary/10 px-3 py-2"
				>
					<div>
						<p class="text-[13px] font-semibold text-on-surface">
							{{ selected.room ? `Room ${selected.room}` : selected.name }} ·
							{{ selected.guests[0]?.guestName }}
						</p>
						<p class="text-[11px] text-on-surface-variant">
							{{ selected.name }} · {{ selected.status }}
							<template
								v-if="
									selected.status !== 'In House' && selected.status !== 'Due Out'
								"
							>
								· services post once the guest has checked in
							</template>
						</p>
					</div>
					<button
						type="button"
						class="text-[12px] font-semibold text-primary"
						@click="selected = null"
					>
						Change
					</button>
				</div>

				<div
					v-for="appointment in activeAppointments"
					:key="appointmentId(appointment)"
					class="rounded-lg border border-outline-variant px-3 py-2 space-y-2"
				>
					<div class="flex items-center justify-between gap-2">
						<p class="text-[13px] font-semibold text-on-surface">
							{{ appointment.serviceType }}
						</p>
						<p class="text-[11px] text-on-surface-variant">
							{{ formatDate(appointment.date) }}
							<template v-if="appointment.startTime">
								· {{ String(appointment.startTime).slice(0, 5) }}</template
							>
						</p>
					</div>
					<div
						v-for="(guest, index) in plan[appointmentId(appointment)]"
						:key="index"
						class="flex items-center gap-2"
					>
						<select
							v-model="plan[appointmentId(appointment)][index]"
							class="flex-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-2 py-1.5 text-[13px]"
							:aria-label="`Who receives ${appointment.serviceType}`"
						>
							<option value="">Who receives it?</option>
							<option
								v-for="option in selected.guests"
								:key="option.name"
								:value="option.name"
								:disabled="!option.canCharge"
							>
								{{ option.guestName }}
								{{ option.role === "Primary" ? "(primary)" : "" }}
								{{ option.canCharge ? "" : "· can't charge to the room" }}
							</option>
						</select>
						<button
							v-if="index > 0"
							type="button"
							class="material-symbols-outlined text-[18px] text-on-surface-variant"
							aria-label="Remove guest"
							@click="plan[appointmentId(appointment)].splice(index, 1)"
						>
							close
						</button>
					</div>
					<button
						v-if="
							!appointment.isCouple &&
							selected.guests.length > plan[appointmentId(appointment)].length
						"
						type="button"
						class="text-[11px] font-semibold text-primary"
						@click="plan[appointmentId(appointment)].push('')"
					>
						+ Shared with another guest (split equally)
					</button>
				</div>

				<p v-if="error" class="text-[12px] text-error">{{ error }}</p>
				<button
					type="button"
					class="w-full bg-primary text-on-primary px-4 py-2.5 rounded-md text-[12px] font-semibold flex items-center justify-center gap-2 disabled:opacity-45 disabled:cursor-not-allowed"
					:disabled="!ready || saving"
					@click="submit"
				>
					<span class="material-symbols-outlined text-[18px]">room_service</span>
					{{ saving ? "Charging…" : confirmLabel }}
				</button>
			</div>
		</template>
	</section>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { chargeBookingToRoomApi, hotelErrorMessage, searchServiceStaysApi } from "@/api/hotel.api";
import { formatDate } from "@/utils/formatters";

const props = defineProps({
	bookingId: { type: String, required: true },
	appointments: { type: Array, default: () => [] },
	collapsible: { type: Boolean, default: false },
	confirmLabel: { type: String, default: "Charge to room and confirm" },
});
const emit = defineEmits(["charged"]);

const INACTIVE = ["Cancelled", "Closed", "No Show", "Rescheduled", "Completed"];

const open = ref(!props.collapsible);
const query = ref("");
const stays = ref([]);
const selected = ref(null);
const searching = ref(false);
const saving = ref(false);
const error = ref("");
const plan = reactive({});
let timer = null;

const appointmentId = (appointment) => appointment.name || appointment.appointmentId;
const activeAppointments = computed(() =>
	props.appointments.filter((appointment) => !INACTIVE.includes(appointment.status))
);
const ready = computed(
	() =>
		selected.value &&
		activeAppointments.value.length &&
		activeAppointments.value.every((appointment) => {
			const guests = plan[appointmentId(appointment)] || [];
			return (
				guests.length && guests.every(Boolean) && new Set(guests).size === guests.length
			);
		})
);

function resetPlan() {
	const guests = selected.value?.guests?.filter((guest) => guest.canCharge) || [];
	activeAppointments.value.forEach((appointment, index) => {
		// A couple booking's second service is usually for the second guest.
		const guess = appointment.isCouple
			? guests[index % Math.max(guests.length, 1)]
			: guests[0];
		plan[appointmentId(appointment)] = [guess?.name || ""];
	});
}

watch(selected, resetPlan);

function searchSoon() {
	window.clearTimeout(timer);
	timer = window.setTimeout(search, 250);
}

async function search() {
	searching.value = true;
	error.value = "";
	try {
		stays.value = (await searchServiceStaysApi(query.value)) || [];
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
	} finally {
		searching.value = false;
	}
}

function choose(stay) {
	selected.value = stay;
}

async function submit() {
	if (!ready.value) return;
	saving.value = true;
	error.value = "";
	try {
		const result = await chargeBookingToRoomApi({
			booking: props.bookingId,
			stay: selected.value.name,
			assignments: activeAppointments.value.map((appointment) => ({
				appointment: appointmentId(appointment),
				guests: plan[appointmentId(appointment)].map((stayGuest) => ({
					stay_guest: stayGuest,
				})),
			})),
		});
		emit("charged", result);
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
	} finally {
		saving.value = false;
	}
}

watch(open, (value) => {
	if (value && !stays.value.length) search();
});
if (open.value) search();
</script>
