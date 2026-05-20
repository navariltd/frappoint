<template>
	<div class="space-y-8">
		<div>
			<p class="text-label-md text-on-surface-variant mb-2">
				Assignment {{ currentIndex + 1 }} of {{ total }}
			</p>
			<h2 class="text-headline-md font-headline-md text-on-surface">
				{{ assignment.service_name }}
			</h2>
			<p class="text-body-md text-on-surface-variant">
				{{ assignment.package_name }} • {{ assignment.duration_minutes }} minutes
			</p>
		</div>

		<div
			v-if="error"
			class="p-4 rounded-lg bg-error-container/30 border border-error-container"
		>
			<div class="flex gap-3">
				<span class="material-symbols-outlined text-error">error</span>
				<p class="text-body-sm text-on-error-container">{{ error }}</p>
			</div>
		</div>

		<section class="space-y-6">
			<div class="flex items-center gap-3 mb-6">
				<span
					class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-on-primary font-bold text-sm"
					>A</span
				>
				<h3 class="text-headline-sm font-headline-sm">Guest Information</h3>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<input
					:value="assignment.guest_full_name"
					type="text"
					placeholder="Full Name"
					class="px-4 py-3 rounded-lg border border-outline-variant bg-surface-container placeholder-on-surface-variant/50 text-on-surface"
					@input="emitGuest('fullName', ($event.target as HTMLInputElement).value)"
				/>
				<input
					:value="assignment.guest_email"
					type="email"
					placeholder="Email Address"
					class="px-4 py-3 rounded-lg border border-outline-variant bg-surface-container placeholder-on-surface-variant/50 text-on-surface"
					@input="emitGuest('email', ($event.target as HTMLInputElement).value)"
				/>
				<input
					:value="assignment.guest_mobile"
					type="tel"
					placeholder="Mobile Number"
					class="px-4 py-3 rounded-lg border border-outline-variant bg-surface-container placeholder-on-surface-variant/50 text-on-surface md:col-span-2"
					@input="emitGuest('mobile', ($event.target as HTMLInputElement).value)"
				/>
			</div>
		</section>

		<section v-if="assignment.guest_full_name" class="space-y-6">
			<div class="flex items-center gap-3 mb-6">
				<span
					class="flex items-center justify-center w-8 h-8 rounded-full"
					:class="
						assignment.selected_date
							? 'bg-primary text-on-primary'
							: 'bg-outline-variant text-on-surface-variant'
					"
					>B</span
				>
				<h3 class="text-headline-sm font-headline-sm">Select Date</h3>
			</div>
			<AppointmentDateSelector
				:dates="assignment.available_dates"
				:selected-date="assignment.selected_date"
				:loading="isLoadingDates"
				@select="$emit('selectDate', $event)"
			/>
		</section>

		<section v-if="assignment.selected_date" class="space-y-6">
			<div class="flex items-center gap-3 mb-6">
				<span
					class="flex items-center justify-center w-8 h-8 rounded-full"
					:class="
						assignment.selected_slot_id
							? 'bg-primary text-on-primary'
							: 'bg-outline-variant text-on-surface-variant'
					"
					>C</span
				>
				<h3 class="text-headline-sm font-headline-sm">Select Time Slot</h3>
			</div>
			<AppointmentSlotSelector
				:slots="assignment.available_slots"
				:selected-slot-id="assignment.selected_slot_id"
				:loading="isLoadingSlots"
				@select="$emit('selectSlot', $event)"
			/>
		</section>
	</div>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import type { GuestAssignment } from "@/stores/bookingWorkflow.store";
import AppointmentDateSelector from "@/components/booking/AppointmentDateSelector.vue";
import AppointmentSlotSelector from "@/components/booking/AppointmentSlotSelector.vue";

const props = defineProps<{
	assignment: GuestAssignment;
	currentIndex: number;
	total: number;
	error?: string;
	isLoadingDates: boolean;
	isLoadingSlots: boolean;
}>();

const guestDraft = reactive({
	fullName: props.assignment.guest_full_name,
	email: props.assignment.guest_email,
	mobile: props.assignment.guest_mobile,
});

const emit = defineEmits<{
	assignGuest: [payload: { fullName: string; email?: string; mobile?: string }];
	selectDate: [date: string];
	selectSlot: [slotId: string];
}>();

function emitGuest(field: "fullName" | "email" | "mobile", value: string) {
	guestDraft[field] = value;
	emit("assignGuest", {
		fullName: guestDraft.fullName,
		email: guestDraft.email,
		mobile: guestDraft.mobile,
	});
}
</script>
