<template>
  <div class="flex h-screen flex-col overflow-hidden p-5">
    <Calendar
      :config="calendarConfig"
      :events="events"
      @click="onEventClick"
      @dblClick="onEventDblClick"
      @cellClick="onCellClick"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
import { Calendar } from 'frappe-ui'

const events = ref([])

const calendarConfig = {
  defaultMode: 'Month',
  isEditMode: false,
  allowCustomClickEvents: true,
  enableShortcuts: false,
}

const loadEvents = async () => {
  const data = await call(
    'frappoint.frappoint.doctype.service_appointment.service_appointment.get_events',
    {
      start: '2025-12-01',
      end: '2025-12-31',
    }
  )

  events.value = data.map(e => ({
    id: e.name,
    title: `${e.customer} • ${e.appointment_provider}`,
    participant: e.appointment_provider,
    venue: e.location || '',
    fromDate: e.start.split(' ')[0],
    toDate: e.end.split(' ')[0],
    fromTime: e.start.split(' ')[1].slice(0, 5),
    toTime: e.end.split(' ')[1].slice(0, 5),
    color: e.color || 'blue',
  }))
}

onMounted(loadEvents)

// Events
const onEventClick = (event) => {
  console.log('Clicked event:', event)
}

const onEventDblClick = (event) => {
  console.log('Double clicked:', event)
}

const onCellClick = (data) => {
  console.log('Clicked empty cell:', data)
}
</script>
 
