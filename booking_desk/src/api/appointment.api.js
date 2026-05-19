import { createResource } from "frappe-ui";

const APPOINTMENT_DOCTYPE = "Service Appointment";

const appointmentFields = [
	"name",
	"appointment_date",
	"start_time",
	"end_time",
	"duration",
	"status",
	"payment_status",
	"outstanding_amount",
	"appointment_provider",
	"full_name",
	"customer",
	"appointment_type",
	"actual_start_time",
	"actual_end_time",
	"modified",
];

const appointmentsResource = createResource({
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

export async function fetchAppointmentsByDateRange({ fromDate, toDate, pageLength = 500 }) {
	const response = await appointmentsResource.fetch({
		doctype: APPOINTMENT_DOCTYPE,
		fields: appointmentFields,
		filters: [["appointment_date", "between", [fromDate, toDate]]],
		order_by: "appointment_date asc, start_time asc",
		limit_page_length: pageLength,
	});

	return unwrapListPayload(response ?? appointmentsResource.data);
}

export { APPOINTMENT_DOCTYPE, appointmentFields, appointmentsResource };
