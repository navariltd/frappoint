<template>
  <div class="p-6">
    <FullCalendar :options="calendarOptions" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { call } from 'frappe-ui'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'

const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  height: 'auto',
  selectable: true,
  editable: false,
  expandRows: true,
  eventDisplay: 'block',



  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },

  events: async (info, success, failure) => {
    try {
      const data = await call(
        'frappoint.frappoint.doctype.service_appointment.service_appointment.get_events',
        {
          start: info.startStr,
          end: info.endStr,
        }
      )

      const events = data.map(e => ({
        id: e.name,
        title: `${e.customer} • ${e.appointment_provider}`,
        start: e.start,
        end: e.end,
        color: e.color,
        allDay: false,
        extendedProps: e,
      }))

      success(events)
    } catch (err) {
      failure(err)
    }
  },

  eventClick(info) {
    console.log(info.event.extendedProps)
  },
})
</script>


