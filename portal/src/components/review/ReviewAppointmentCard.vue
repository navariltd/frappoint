<template>
	<div class="rounded-xl border border-outline-variant/20 bg-surface p-5 space-y-3">
		<!-- Guest + service row -->
		<div class="flex items-start justify-between gap-3">
			<div class="space-y-0.5">
				<p class="text-body-md font-semibold text-on-surface">
					{{ appointment.guestName || "Guest" }}
				</p>
				<p class="text-body-sm text-on-surface-variant">{{ appointment.serviceType }}</p>
			</div>
			<span
				v-if="appointment.appointmentCouponCode"
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-label-xs font-semibold shrink-0"
			>
				<span class="material-symbols-outlined text-[12px]">local_offer</span>
				{{ appointment.appointmentCouponCode }}
			</span>
		</div>

		<!-- Date / time / provider row -->
		<div class="flex flex-wrap gap-x-4 gap-y-1 text-body-sm text-on-surface-variant">
			<span v-if="appointment.date" class="flex items-center gap-1">
				<span class="material-symbols-outlined text-[15px]">calendar_today</span>
				{{ formatDate(appointment.date) }}
			</span>
			<span v-if="appointment.startTime" class="flex items-center gap-1">
				<span class="material-symbols-outlined text-[15px]">schedule</span>
				{{ formatTime(appointment.startTime) }}
				<template v-if="appointment.endTime">
					– {{ formatTime(appointment.endTime) }}</template
				>
			</span>
			<span v-if="appointment.provider" class="flex items-center gap-1">
				<span class="material-symbols-outlined text-[15px]">person</span>
				{{ appointment.provider }}
			</span>
		</div>

		<!-- Pricing row -->
		<div class="flex items-end justify-between border-t border-outline-variant/20 pt-3 gap-2">
			<div class="space-y-0.5">
				<div class="flex items-center gap-2">
					<span class="text-body-sm text-on-surface-variant">Base</span>
					<span class="text-body-sm font-medium text-on-surface">{{
						fmt(appointment.baseAmount)
					}}</span>
				</div>
				<div
					v-if="appointment.appointmentDiscountAmount > 0"
					class="flex items-center gap-2"
				>
					<span class="text-body-sm text-on-surface-variant">Discount</span>
					<span class="text-body-sm font-medium text-secondary"
						>–{{ fmt(appointment.appointmentDiscountAmount) }}</span
					>
				</div>
			</div>
			<div class="text-right">
				<p
					class="text-label-xs uppercase tracking-wider text-on-surface-variant font-semibold"
				>
					Appointment Total
				</p>
				<p class="text-body-lg font-bold text-on-surface">
					{{ fmt(appointment.finalAmount) }}
				</p>
			</div>
		</div>

		<!-- Per-appointment coupon section -->
		<div class="border-t border-outline-variant/20 pt-3">
			<!-- Booking coupon lock notice -->
			<div
				v-if="isBookingCouponActive"
				class="flex items-center gap-2 text-label-sm text-on-surface-variant opacity-70"
			>
				<span class="material-symbols-outlined text-[14px]">lock</span>
				Booking-level coupon active
			</div>

			<!-- Applied appointment coupon -->
			<div
				v-else-if="appointment.appointmentCouponCode"
				class="flex items-center justify-between gap-3"
			>
				<div class="flex items-center gap-2">
					<span class="material-symbols-outlined text-secondary text-[16px]"
						>check_circle</span
					>
					<span class="text-label-sm font-semibold text-on-surface">
						{{ appointment.appointmentCouponCode }}
					</span>
					<span class="text-label-xs text-on-surface-variant">applied</span>
				</div>
				<button
					:disabled="isApplying"
					class="flex items-center gap-1 text-label-sm font-semibold text-error hover:opacity-75 transition-opacity disabled:opacity-40"
					@click="$emit('remove')"
				>
					<span
						v-if="isApplying"
						class="w-3 h-3 border-2 border-error/30 border-t-error rounded-full animate-spin"
					></span>
					<span v-else class="material-symbols-outlined text-[14px]">close</span>
					Remove
				</button>
			</div>

			<!-- Coupon input -->
			<div v-else class="space-y-1.5">
				<div class="flex gap-2">
					<input
						:value="couponDraft"
						type="text"
						placeholder="Add coupon for this appointment"
						:disabled="isApplying"
						class="flex-1 px-3 py-2 rounded-lg border border-outline-variant/40 bg-surface-container text-body-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all disabled:opacity-50"
						@input="
							$emit('update:couponDraft', ($event.target as HTMLInputElement).value)
						"
						@keydown.enter.prevent="$emit('apply')"
					/>
					<button
						:disabled="isApplying || !couponDraft?.trim()"
						class="px-4 py-2 rounded-lg bg-secondary text-on-secondary font-semibold text-label-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shrink-0"
						@click="$emit('apply')"
					>
						<span
							v-if="isApplying"
							class="w-3.5 h-3.5 border-2 border-on-secondary/30 border-t-on-secondary rounded-full animate-spin"
						></span>
						<span v-else>Apply</span>
					</button>
				</div>
				<p v-if="couponError" class="text-label-xs text-error flex items-center gap-1">
					<span class="material-symbols-outlined text-[12px]">error</span>
					{{ couponError }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils";
import type { AppointmentPricingBreakdown } from "@/services/checkout.service";

const props = defineProps<{
	appointment: AppointmentPricingBreakdown;
	currency: string;
	couponDraft?: string;
	couponError?: string;
	isApplying?: boolean;
	isBookingCouponActive?: boolean;
}>();

defineEmits<{
	"update:couponDraft": [value: string];
	apply: [];
	remove: [];
}>();

function fmt(amount: number) {
	return formatCurrency(Number(amount || 0), props.currency);
}

function formatDate(dateStr: string) {
	if (!dateStr) return "";
	try {
		return new Date(dateStr).toLocaleDateString(undefined, {
			weekday: "short",
			month: "short",
			day: "numeric",
		});
	} catch {
		return dateStr;
	}
}

function formatTime(timeStr: string) {
	if (!timeStr) return "";
	try {
		const [h, m] = timeStr.split(":");
		const d = new Date();
		d.setHours(Number(h), Number(m));
		return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
	} catch {
		return timeStr;
	}
}
</script>
