frappe.views.calendar["Service Appointment"] = {
	field_map: {
		start: "start",
		end: "end",
		id: "name",
		title: "customer",
		allDay: "allDay",
		eventColor: "color",
	},
	order_by: "appointment_date",
	gantt: true,
	get_events_method:
		"frappoint.frappoint.doctype.service_appointment.service_appointment.get_events",
};
