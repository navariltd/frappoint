<template>
	<section
		v-if="stay"
		class="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-4 lg:p-5 shadow-sm space-y-3"
	>
		<div class="flex items-start justify-between gap-3">
			<div>
				<p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-outline">
					Hotel stay
				</p>
				<h2 class="mt-1 text-base font-semibold tracking-tight text-on-surface">
					{{ stay.room ? `Room ${stay.room}` : stay.stay }}
					<span v-if="stay.guestName" class="font-normal text-on-surface-variant">
						· {{ stay.guestName }}
					</span>
				</h2>
				<p class="text-[12px] text-on-surface-variant">
					<RouterLink
						:to="{ name: 'HotelStay', params: { stayId: stay.stay } }"
						class="text-primary font-semibold"
						>{{ stay.stay }}</RouterLink
					>
					· {{ stay.stayStatus }} · {{ formatDate(stay.arrival) }} –
					{{ formatDate(stay.departure) }}
				</p>
			</div>
			<span
				class="rounded-full px-2.5 py-1 text-[11px] font-semibold"
				:class="
					stay.chargeToRoom
						? 'bg-primary/10 text-primary'
						: 'bg-surface-container-high text-on-surface-variant'
				"
			>
				{{ stay.chargeToRoom ? "Charged to room" : "Paid at the desk" }}
			</span>
		</div>

		<ul v-if="stay.participants.length" class="divide-y divide-outline-variant/40 text-[13px]">
			<li
				v-for="row in stay.participants"
				:key="row.name"
				class="py-2 flex flex-wrap items-center justify-between gap-2"
			>
				<div class="min-w-0">
					<p class="font-semibold text-on-surface">
						{{ row.guest_name }}
						<span class="font-normal text-on-surface-variant"
							>· {{ row.service_type }}</span
						>
					</p>
					<p class="text-[11px] text-on-surface-variant">
						{{ row.service_appointment }}
						<template v-if="row.share_percent < 100">
							· {{ Number(row.share_percent).toFixed(0) }}% share</template
						>
						<template v-if="row.posted_folio">
							· folio {{ row.posted_folio }}</template
						>
						<template v-if="row.fee_amount">
							· {{ row.fee_waived ? "fee waived" : "fee" }}
							{{ money(row.fee_amount) }}</template
						>
					</p>
					<p v-if="row.posting_error" class="text-[11px] text-error">
						{{ row.posting_error }}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<span class="text-[12px] font-semibold">{{ money(row.amount) }}</span>
					<span
						class="rounded-full px-2 py-0.5 text-[10px] font-semibold"
						:class="statusClass(row.status)"
						>{{ row.status }}</span
					>
					<button
						v-if="row.status === 'Failed'"
						type="button"
						class="text-[11px] font-semibold text-primary disabled:opacity-50"
						:disabled="busy"
						@click="retry(row.service_appointment)"
					>
						Retry
					</button>
				</div>
			</li>
		</ul>

		<form v-if="stay.canUnlink && releasing" class="space-y-2" @submit.prevent="release">
			<label class="block text-[12px] text-on-surface-variant">
				Why will the guest pay at the desk instead?
				<input
					v-model="reason"
					class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
					required
				/>
			</label>
			<div class="flex gap-2">
				<button
					type="submit"
					class="rounded-md bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
					:disabled="busy || !reason.trim()"
				>
					Take back to desk payment
				</button>
				<button
					type="button"
					class="text-[12px] font-semibold text-on-surface-variant"
					@click="releasing = false"
				>
					Keep on the room
				</button>
			</div>
		</form>
		<button
			v-else-if="stay.canUnlink"
			type="button"
			class="text-[12px] font-semibold text-primary"
			@click="releasing = true"
		>
			Pay at the desk instead
		</button>
		<p v-if="error" class="text-[12px] text-error">{{ error }}</p>
	</section>

	<RoomChargePanel
		v-else-if="canCharge"
		:booking-id="booking.bookingId"
		:appointments="booking.appointments"
		collapsible
		confirm-label="Charge to room"
		@charged="$emit('changed')"
	/>
</template>

<script setup>
import { computed, ref } from "vue";
import RoomChargePanel from "@/components/booking/RoomChargePanel.vue";
import {
	hotelErrorMessage,
	releaseBookingToDeskApi,
	retryServicePostingApi,
} from "@/api/hotel.api";
import { formatDate } from "@/utils/formatters";

const props = defineProps({ booking: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const stay = computed(() => props.booking.roomCharge?.hotelStay || null);
const canCharge = computed(
	() =>
		Boolean(props.booking.roomCharge?.canCharge) &&
		Number(props.booking.paidAmount || 0) <= 0 &&
		props.booking.status !== "Cancelled"
);
const releasing = ref(false);
const reason = ref("");
const busy = ref(false);
const error = ref("");

function money(value) {
	return `${props.booking.currency || "KES"} ${Number(value || 0).toFixed(2)}`;
}

function statusClass(status) {
	if (status === "Posted") return "bg-tertiary-container text-on-tertiary-container";
	if (status === "Failed") return "bg-error/10 text-error";
	if (status === "Pending") return "bg-secondary-container text-on-secondary-container";
	return "bg-surface-container-high text-on-surface-variant";
}

async function run(action) {
	busy.value = true;
	error.value = "";
	try {
		await action();
		emit("changed");
		return true;
	} catch (failure) {
		error.value = hotelErrorMessage(failure);
		return false;
	} finally {
		busy.value = false;
	}
}

const retry = (appointment) => run(() => retryServicePostingApi(appointment));

async function release() {
	const done = await run(() => releaseBookingToDeskApi(props.booking.bookingId, reason.value));
	if (done) {
		releasing.value = false;
		reason.value = "";
	}
}
</script>
