<template>
	<div class="flex items-start justify-between gap-3 mt-1">
		<div class="min-w-0 flex-1">
			<h4 class="text-[13px] font-semibold text-on-surface truncate">
				{{ appointment.fullName }}
			</h4>
			<p class="text-[12px] text-on-surface-variant truncate mt-0.5">
				{{ appointment.serviceType }}
			</p>
		</div>
	</div>
</template>

<script setup>
defineProps({ appointment: { type: Object, required: true } });
</script>
