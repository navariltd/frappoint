<template>
	<div class="rounded-xl border border-outline-variant bg-surface p-4 space-y-3">
		<p class="text-[13px] font-semibold text-on-surface">Mpesa STK Push</p>
		<div>
			<label class="block text-[12px] text-on-surface-variant mb-1">Phone Number</label>
			<input
				type="text"
				:value="phoneNumber"
				class="w-full rounded-lg border border-outline px-3 py-2 text-[13px]"
				placeholder="e.g. 2547XXXXXXXX"
				@input="$emit('update:phoneNumber', $event.target.value)"
			/>
		</div>
		<p class="text-[11px] text-on-surface-variant">
			Trigger sends STK to customer mobile and keeps this session in pending confirmation.
		</p>
	</div>
</template>

<script setup>
defineProps({
	phoneNumber: { type: String, default: "" },
});

defineEmits(["update:phoneNumber"]);
</script>
