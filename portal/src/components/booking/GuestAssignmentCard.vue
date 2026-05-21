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

	<section
		class="bg-white rounded-xl custom-shadow p-6 transition-all duration-300 border border-transparent hover:border-primary-container group"
	>
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-4">
				<div class="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
					<img
						class="w-full h-full object-cover"
						data-alt="A tranquil high-end spa room with warm wooden accents and soft ambient lighting. A professional massage table is centered, draped in plush white linens. In the background, a single green plant and minimalist decor create a sense of professional serenity and luxury, illuminated by gentle natural light filtering through sheer curtains."
						src="https://lh3.googleusercontent.com/aida-public/AB6AXuAAY2TxnoZeoJgBIO1Z32AHdIQfoRcuuI1Gog-c1V9df9whsLSQGNRLTmv2C6dVMlomeVYHCY4QeAC0GEArVWKUz9eo72qZa_eJEdyWqo13XMGRq6v4ArtRWv76No3s3exNcmPJS7IRQesUteHfppZodBHrTR_sMhwsS43bR77wCnkZIqNCqA0KmvnSVbYTkY3zUxpIaJ1JM7LvJt7xpSBy0Lkyb6vntRL_KxHPMJuH3_UX3w1H0C6TVkpoK6izd1URORTQv_ZWc3Uj"
					/>
				</div>
				<div>
					<h3 class="font-headline-sm text-headline-sm text-on-surface">
						Deep Tissue Massage
					</h3>
					<p class="font-label-sm text-on-surface-variant">
						60 Minutes • Specialist Room 04
					</p>
				</div>
			</div>
			<div class="hidden group-[.is-filled]:flex items-center gap-2 text-primary">
				<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
					>check_circle</span
				>
				<span class="font-label-md">Assigned</span>
			</div>
		</div>
		<!-- Guest 1 -->
		<div class="space-y-4">
			<div class="flex items-center justify-between">
				<label class="font-label-md text-on-surface">Guest 1</label>
				<button
					class="text-primary font-label-sm hover:underline transition-all flex items-center gap-1"
				>
					<span class="material-symbols-outlined text-[16px]">calendar_clock</span>
					Pick Time Slot
				</button>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Full Name"
						type="text"
						value="Emmanuel Smith"
					/>
				</div>
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Email Address (Optional)"
						type="email"
					/>
				</div>
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Phone Number (Optional)"
						type="phone"
					/>
				</div>
			</div>
		</div>

		<!-- Guest 2  -->
		<div class="space-y-4">
			<div class="flex items-center justify-between">
				<label class="font-label-md text-on-surface">Guest 2</label>
				<button
					class="text-primary font-label-sm hover:underline transition-all flex items-center gap-1"
				>
					<span class="material-symbols-outlined text-[16px]">calendar_clock</span>
					Pick Time Slot
				</button>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Full Name"
						type="text"
						value="Jane Doe"
					/>
				</div>
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Email Address (Optional)"
						type="email"
					/>
				</div>
				<div class="relative">
					<input
						class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
						placeholder="Phone Number (Optional)"
						type="phone"
					/>
				</div>
			</div>
		</div>
	</section>
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
