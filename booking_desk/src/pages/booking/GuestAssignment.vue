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
				Assign each selected service to guests, choose date, then pick slots.
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
	updateGuestFromCustomer,
	quickCreateGuest,
	updateProviderPreference,
	clearGuest,
	fetchGuestDates,
	selectGuestDate,
	selectGuestSlot,
} = useGuestAssignment();

const { selectedSlotCount, pendingSlotCount } = useSlotSelection(assignments);
useAvailability({ isLoadingDates, isLoadingSlots, errorByGuest });

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
