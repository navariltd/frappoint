import { createResource } from "frappe-ui";

const UPSERT_DRAFT_APPOINTMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.upsert_draft_service_appointment";

const upsertDraftAppointmentResource = createResource({
	url: UPSERT_DRAFT_APPOINTMENT_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function upsertDraftServiceAppointmentApi({ bookingId, appointmentId, assignment }) {
	const response = await upsertDraftAppointmentResource.fetch({
		booking_id: bookingId,
		appointment_id: appointmentId || undefined,
		assignment: JSON.stringify(assignment || {}),
	});
	return unwrapPayload(response ?? upsertDraftAppointmentResource.data);
}
