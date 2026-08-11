<template>
	<section
		class="rounded-xl border border-outline-variant bg-surface-container-lowest overflow-hidden"
		:class="isActive ? 'shadow-[0_4px_20px_rgba(45,52,54,0.06)]' : ''"
	>
		<!-- Collapsible header -->
		<button
			type="button"
			class="w-full flex items-center justify-between gap-3 px-4 py-3.5 text-left hover:bg-surface-container/40 transition-colors"
			@click="isExpanded = !isExpanded"
		>
			<div class="flex items-center gap-2 min-w-0">
				<span
					class="material-symbols-outlined text-[18px] text-on-surface-variant shrink-0 transition-transform duration-200"
					:class="isExpanded ? '' : '-rotate-90'"
					>expand_more</span
				>
				<div class="min-w-0">
					<p class="text-[13px] font-semibold text-on-surface truncate">
						{{ service.serviceName }}
					</p>
					<p class="text-[11px] text-on-surface-variant">
						{{ service.duration }} min · {{ service.packageName }}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<span class="text-[11px] text-on-surface-variant"
					>{{ completedGuests }}/{{ service.quantity }}</span
				>
				<span
					class="rounded-full px-2 py-0.5 text-[10px] font-semibold"
					:class="
						completedGuests === service.quantity
							? 'bg-tertiary-container text-on-tertiary-container'
							: 'bg-secondary-container text-on-secondary-container'
					"
				>
					{{ completedGuests === service.quantity ? "Complete" : "In Progress" }}
				</span>
			</div>
		</button>

		<!-- Collapsible body -->
		<div v-show="isExpanded" class="px-4 pb-4 pt-1 border-t border-outline-variant space-y-3">
			<GuestAssignmentSection
				:guests="service.guests"
				:quantity="service.quantity"
				:customers="customers"
				:providerOptions="service.providerOptions || []"
				:isLoadingDates="isLoadingDates"
				:isLoadingSlots="isLoadingSlots"
				:isReservingSlots="isReservingSlots"
				:reservingSlotIdByGuest="reservingSlotIdByGuest"
				:errorByGuest="errorByGuest"
				@select-customer="
					(guestKey, customerId) =>
						$emit('select-customer', service.serviceKey, guestKey, customerId)
				"
				@quick-create="
					(guestKey, payload) =>
						$emit('quick-create', service.serviceKey, guestKey, payload)
				"
				@provider-preference="
					(guestKey, providerId) =>
						$emit('provider-preference', service.serviceKey, guestKey, providerId)
				"
				@notes-change="
					(guestKey, notes) => $emit('notes-change', service.serviceKey, guestKey, notes)
				"
				@clear-guest="(guestKey) => $emit('clear-guest', service.serviceKey, guestKey)"
				@load-dates="(guestKey) => $emit('load-dates', service.serviceKey, guestKey)"
				@select-date="
					(guestKey, date) => $emit('select-date', service.serviceKey, guestKey, date)
				"
				@select-slot="
					(guestKey, slotId) =>
						$emit('select-slot', service.serviceKey, guestKey, slotId)
				"
			/>
		</div>
	</section>
</template>

<script setup>
import { ref, computed } from "vue";
import GuestAssignmentSection from "./GuestAssignmentSection.vue";

const props = defineProps({
	service: {
		type: Object,
		required: true,
	},
	customers: {
		type: Array,
		default: () => [],
	},
	isLoadingDates: {
		type: Object,
		default: () => ({}),
	},
	isLoadingSlots: {
		type: Object,
		default: () => ({}),
	},
	isReservingSlots: {
		type: Object,
		default: () => ({}),
	},
	reservingSlotIdByGuest: {
		type: Object,
		default: () => ({}),
	},
	errorByGuest: {
		type: Object,
		default: () => ({}),
	},
	isActive: {
		type: Boolean,
		default: false,
	},
});

defineEmits([
	"select-customer",
	"quick-create",
	"provider-preference",
	"notes-change",
	"clear-guest",
	"load-dates",
	"select-date",
	"select-slot",
]);

const isExpanded = ref(true);

const completedGuests = computed(
	() => props.service.guests.filter((guest) => guest.isComplete).length
);
</script>
