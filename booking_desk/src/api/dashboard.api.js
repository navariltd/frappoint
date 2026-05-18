import { createResource } from "frappe-ui";
import { APPOINTMENT_DOCTYPE, appointmentFields } from "./appointment.api";

const dashboardAppointmentsResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

const unwrapListPayload = (payload) => {
	if (Array.isArray(payload)) {
		return payload;
	}
	if (Array.isArray(payload?.message)) {
		return payload.message;
	}
	return [];
};

export async function fetchDashboardAppointmentsForDate(date) {
	const response = await dashboardAppointmentsResource.fetch({
		doctype: APPOINTMENT_DOCTYPE,
		fields: appointmentFields,
		filters: [["appointment_date", "=", date]],
		order_by: "start_time asc",
		limit_page_length: 1000,
	});

	return unwrapListPayload(response ?? dashboardAppointmentsResource.data);
}

export { dashboardAppointmentsResource };
