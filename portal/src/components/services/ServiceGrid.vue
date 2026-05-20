<template>
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
		<ServiceCard
			v-for="service in services"
			:key="service.name"
			:service="service"
			@view="$emit('view', $event)"
			@add="$emit('add', $event)"
		/>
	</div>
</template>

<script setup>
import ServiceCard from "@/components/services/ServiceCard.vue";

defineProps({
	services: { type: Array, default: () => [] },
});

defineEmits(["view", "add"]);
</script>
