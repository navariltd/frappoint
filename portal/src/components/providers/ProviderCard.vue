<template>
	<div
		class="bg-white flex items-center gap-4 p-4 rounded-lg border border-slate-100 shadow-sm hover:shadow-md transition-shadow"
	>
		<img
			class="size-16 object-cover rounded-full"
			:src="provider.image || profilePlaceholder"
			:alt="provider.name"
		/>
		<div class="px-2">
			<h2 class="font-bold text-xl mb-1">{{ provider.provider_name }}</h2>
			<p class="text-gray-700">{{ provider.designation }}</p>
		</div>
	</div>
</template>

<script setup>
import profilePlaceholder from "@/assets/images/profile-circle.svg";

defineProps({
	provider: Object,
});
</script>
