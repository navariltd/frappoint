<template>
  <AppLayout>
    <main class="flex-1 p-8 overflow-auto">
      <Appointments :username="userDocResource.data.full_name" />
    </main>
  </AppLayout>
</template>

<script setup>
import Appointments from "../components/Appointments.vue";
import { useUserStore } from "../data/user";
import AppLayout from "../components/AppLayout.vue";

const { userDocResource } = useUserStore();
</script>
