<template>
	<div class="h-full flex flex-col">
		<header class="px-4 py-4 border-b border-outline-variant bg-surface-container-lowest">
			<div class="flex items-center gap-2 text-on-surface-variant mb-1">
				<span class="text-[11px] uppercase tracking-wider text-primary font-semibold">
					Booking Builder
				</span>
				<span class="material-symbols-outlined text-sm">chevron_right</span>
				<span class="text-[11px]">Step 2 of 3</span>
			</div>
			<h1 class="text-[20px] font-semibold text-on-surface">Assign Guests and Schedule</h1>
			<p class="text-[13px] text-on-surface-variant">
				{{
					isCoupleMode
						? "Assign both guests, then choose a time when both providers are available."
						: "Assign each selected service to guests, choose date, then pick slots."
				}}
			</p>
			<div
				class="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-on-surface-variant"
			>
				<span v-if="draftBooking?.name">Draft {{ draftBooking.name }}</span>
				<span>{{ progress.completedGuests }}/{{ progress.totalGuests }} completed</span>
				<span>{{ selectedSlotCount }} slot(s) selected</span>
				<span>{{ pendingSlotCount }} slot(s) pending</span>
			</div>
		</header>

		<div class="flex-1 min-h-0 flex flex-col md:flex-row">
			<section class="flex-1 min-w-0 p-4 overflow-y-auto space-y-4">
				<AssignmentValidationBanner :issues="validationIssues" />

				<AssignmentLoadingState v-if="!assignments.length" />

				<CoupleAssignmentCard
					v-else-if="isCoupleMode"
					:pairs="coupleEntries"
					:customers="customers"
					:dates="coupleAvailableDates"
					:slots="coupleAvailableSlots"
					:selectedDate="coupleSelectedDate"
					:isLoadingDates="isCoupleLoadingDates"
					:isLoadingSlots="isCoupleLoadingSlots"
					:isReserving="isCoupleReserving"
					:reservingSlotId="coupleReservingSlotId"
					:error="coupleError"
					@select-customer="onSelectCustomer"
					@quick-create="onQuickCreateGuest"
					@provider-preference="onProviderPreferenceChange"
					@notes-change="onGuestNotesChange"
					@load-dates="onLoadCoupleDates"
					@select-date="onSelectCoupleDate"
					@select-slot="onSelectCoupleSlot"
				/>

				<div v-else class="space-y-4">
					<ServiceAssignmentCard
						v-for="(service, serviceIndex) in assignments"
						:key="service.serviceKey"
						:service="service"
						:customers="customers"
						:isLoadingDates="isLoadingDates"
						:isLoadingSlots="isLoadingSlots"
						:isReservingSlots="isReservingSlots"
						:reservingSlotIdByGuest="reservingSlotIdByGuest"
						:errorByGuest="errorByGuest"
						:isActive="serviceIndex === activeServiceIndex"
						@select-customer="onSelectCustomer"
						@quick-create="onQuickCreateGuest"
						@provider-preference="onProviderPreferenceChange"
						@notes-change="onGuestNotesChange"
						@clear-guest="onClearGuest"
						@load-dates="onLoadGuestDates"
						@select-date="onSelectGuestDate"
						@select-slot="onSelectGuestSlot"
					/>
				</div>
			</section>

			<AssignmentSummarySidebar
				:summaryRows="summaryRows"
				:progress="progress"
				:isComplete="isComplete"
				:total="formattedTotal"
				@proceed="onProceedToPayment"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import AssignmentLoadingState from "@/components/booking/guest-assignment/AssignmentLoadingState.vue";
import AssignmentSummarySidebar from "@/components/booking/guest-assignment/AssignmentSummarySidebar.vue";
import AssignmentValidationBanner from "@/components/booking/guest-assignment/AssignmentValidationBanner.vue";
import CoupleAssignmentCard from "@/components/booking/guest-assignment/CoupleAssignmentCard.vue";
import ServiceAssignmentCard from "@/components/booking/guest-assignment/ServiceAssignmentCard.vue";
import { useAvailability } from "@/composables/booking/guest-assignment/useAvailability";
import { useGuestAssignment } from "@/composables/booking/guest-assignment/useGuestAssignment";
import { useSlotSelection } from "@/composables/booking/guest-assignment/useSlotSelection";

const router = useRouter();

const {
	assignments,
	activeServiceIndex,
	isLoadingDates,
	isLoadingSlots,
	isReservingSlots,
	reservingSlotIdByGuest,
	errorByGuest,
	progress,
	validationIssues,
	isComplete,
	summaryRows,
	draftBooking,
	grandTotal,
	customers,
	isCoupleMode,
	coupleEntries,
	coupleAvailableDates,
	coupleAvailableSlots,
	coupleSelectedDate,
	coupleError,
	fetchCoupleDates,
	selectCoupleDate,
	selectCoupleSlot,
	updateGuestFromCustomer,
	quickCreateGuest,
	updateProviderPreference,
	updateGuestNotes,
	clearGuest,
	fetchGuestDates,
	selectGuestDate,
	selectGuestSlot,
} = useGuestAssignment();

const { selectedSlotCount, pendingSlotCount } = useSlotSelection(assignments);
useAvailability({ isLoadingDates, isLoadingSlots, errorByGuest });

const coupleGuestKeys = computed(() => coupleEntries.value.map((entry) => entry.guest.guestKey));
const isCoupleLoadingDates = computed(() =>
	coupleGuestKeys.value.some((guestKey) => Boolean(isLoadingDates.value[guestKey]))
);
const isCoupleLoadingSlots = computed(() =>
	coupleGuestKeys.value.some((guestKey) => Boolean(isLoadingSlots.value[guestKey]))
);
const isCoupleReserving = computed(() =>
	coupleGuestKeys.value.some((guestKey) => Boolean(isReservingSlots.value[guestKey]))
);
const coupleReservingSlotId = computed(() => {
	const guestKey = coupleGuestKeys.value.find((key) => reservingSlotIdByGuest.value[key]);
	return guestKey ? reservingSlotIdByGuest.value[guestKey] : "";
});

const formattedTotal = computed(() => {
	const firstCurrency = assignments.value[0]?.currency || "KES";
	return `${firstCurrency} ${Number(grandTotal.value || 0).toFixed(2)}`;
});

const onSelectCustomer = async (serviceKey, guestKey, customerId) => {
	updateGuestFromCustomer(serviceKey, guestKey, customerId);
	await fetchGuestDates(serviceKey, guestKey);
};

const onQuickCreateGuest = async (serviceKey, guestKey, payload) => {
	quickCreateGuest(serviceKey, guestKey, payload);
	await fetchGuestDates(serviceKey, guestKey);
};

const onProviderPreferenceChange = async (serviceKey, guestKey, providerId) => {
	await updateProviderPreference(serviceKey, guestKey, providerId);
};

const onGuestNotesChange = async (serviceKey, guestKey, notes) => {
	await updateGuestNotes(serviceKey, guestKey, notes);
};

const onClearGuest = (serviceKey, guestKey) => {
	clearGuest(serviceKey, guestKey);
};

const onLoadGuestDates = async (serviceKey, guestKey) => {
	await fetchGuestDates(serviceKey, guestKey);
};

const onSelectGuestDate = async (serviceKey, guestKey, date) => {
	await selectGuestDate(serviceKey, guestKey, date);
};

const onSelectGuestSlot = async (serviceKey, guestKey, slotId) => {
	await selectGuestSlot(serviceKey, guestKey, slotId);
};

const onLoadCoupleDates = async () => {
	await fetchCoupleDates();
};

const onSelectCoupleDate = async (date) => {
	await selectCoupleDate(date);
};

const onSelectCoupleSlot = async (slotId) => {
	await selectCoupleSlot(slotId);
};

const onProceedToPayment = () => {
	if (!isComplete.value) {
		return;
	}

	router.push({
		name: "Checkout",
		query: draftBooking.value?.name ? { booking_id: draftBooking.value.name } : undefined,
	});
};
</script>
