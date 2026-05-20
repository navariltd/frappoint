<template>
	<section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
		<OperationalSummaryCards v-for="card in cards" :key="card.key" v-bind="card" />
	</section>
</template>

<script setup>
import OperationalSummaryCards from "@/components/dashboard/OperationalSummaryCards.vue";

defineProps({
	cards: { type: Array, default: () => [] },
});
</script>
