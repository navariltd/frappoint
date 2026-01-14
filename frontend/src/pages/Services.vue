<template>
  <AppLayout>
    <main class="p-6">
      <h1 class="text-2xl font-bold mb-6">Appointment Type</h1>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <ServiceCard
          v-for="service in services"
          :key="service.name"
          :service="service"
          @book="bookService"
        />
      </div>
    </main>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { call } from "frappe-ui"
import AppLayout from "@/components/AppLayout.vue"
import ServiceCard from "@/components/ServiceCard.vue"

const services = ref([])

const loadServices = async () => {
  services.value = await call(
    "frappoint.frappoint.doctype.appointment_type.appointment_type.get_service_cards"
  )
}

const bookService = (service) => {
  console.log("Book clicked:", service)
  // next step → router push to calendar
}

onMounted(loadServices)
</script>
