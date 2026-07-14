import { createResource } from "frappe-ui";

const UPSERT_DRAFT_APPOINTMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.upsert_draft_service_appointment";
const UPDATE_DRAFT_APPOINTMENT_NOTES_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.update_draft_service_appointment_notes";

const upsertDraftAppointmentResource = createResource({
	url: UPSERT_DRAFT_APPOINTMENT_ENDPOINT,
	auto: false,
});

const updateDraftAppointmentNotesResource = createResource({
	url: UPDATE_DRAFT_APPOINTMENT_NOTES_ENDPOINT,
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

export async function updateDraftServiceAppointmentNotesApi({ appointmentId, notes }) {
	const response = await updateDraftAppointmentNotesResource.fetch({
		appointment_id: appointmentId,
		notes: notes || "",
	});
	return unwrapPayload(response ?? updateDraftAppointmentNotesResource.data);
}
