<template>
  <div class="bg-white rounded-xl shadow p-4 hover:shadow-lg transition">
    <img
      :src="service.custom_image || '/placeholder.png'"
      class="h-40 w-full object-cover rounded-lg"
    />

    <h3 class="mt-3 text-lg font-semibold">
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
</template>

<script setup>
defineProps({
  service: Object
})
</script>

