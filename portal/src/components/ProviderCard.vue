<template>
	<div
		class="bg-white flex items-center gap-4 p-4 rounded-lg border border-slate-100 shadow-sm hover:shadow-md transition-shadow"
	>
		<img
			class="size-16 object-cover rounded-full"
			:src="provider.image"
			:alt="provider.name"
		/>
		<div>
			<h2>{{ provider.provider_name }}</h2>
			<p>{{ provider.designation }}</p>
		</div>
	</div>
</template>

<script setup>
defineProps({
	provider: Object,
});
</script>
