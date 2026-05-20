<template>
	<button
		type="button"
		class="relative material-symbols-outlined text-on-surface-variant hover:bg-primary-container/10 p-2 rounded-full transition-all"
		aria-label="Open bookings"
		@click="$emit('open')"
	>
		shopping_bag
		<span
			v-if="count > 0"
			class="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-on-primary text-[10px] leading-[18px] text-center"
		>
			{{ count > 99 ? "99+" : count }}
		</span>
	</button>
</template>

<script setup>
defineProps({
	count: { type: Number, default: 0 },
});

defineEmits(["open"]);
</script>
