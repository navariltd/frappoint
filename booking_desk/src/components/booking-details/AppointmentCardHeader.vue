<template>
	<div class="flex items-start justify-between gap-3 mt-1">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2 min-w-0">
				<h4 class="text-[13px] font-semibold text-on-surface truncate">
					{{ appointment.fullName }}
				</h4>
				<span
					v-if="appointment.isCouple"
					class="shrink-0 rounded-full bg-primary-container px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-on-primary-container"
				>
					{{ appointment.isPrimaryInCouple ? "Couple · Primary" : "Couple · Partner" }}
				</span>
			</div>
			<p class="text-[12px] text-on-surface-variant truncate mt-0.5">
				{{ appointment.serviceType }}
			</p>
			<p
				v-if="appointment.coupleAppointmentId"
				class="text-[10px] text-primary truncate mt-0.5"
			>
				Linked to {{ appointment.coupleAppointmentId }}
			</p>
		</div>
	</div>
</template>

<script setup>
defineProps({ appointment: { type: Object, required: true } });
</script>
