<template>
	<div
		class="bg-white rounded-xl shadow transition-all duration-300 hover:shadow-xl hover:-translate-y-1"
	>
		
		<img
			:src="service.custom_image || '/placeholder.png'"
			class="h-40 w-full object-cover rounded-t-xl"
		/>

		<div class="p-4">
			<h3 class="text-lg font-semibold">
				{{ service.appointment_type }}
			</h3>

			<p class="text-sm text-gray-600 mt-1 line-clamp-3">
				{{ service.description }}
			</p>

			<button
				class="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg"
				@click="$emit('book', service)"
			>
				Book Now
			</button>
		</div>
	</div>
</template>

<script setup>
defineProps({
	service: Object,
});
</script>
