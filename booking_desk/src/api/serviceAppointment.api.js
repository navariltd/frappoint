import { createResource } from "frappe-ui";

const UPSERT_DRAFT_APPOINTMENT_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.upsert_draft_service_appointment";
const UPDATE_DRAFT_APPOINTMENT_NOTES_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.update_draft_service_appointment_notes";
const UPSERT_DRAFT_COUPLE_APPOINTMENTS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.upsert_draft_couple_appointments";

const upsertDraftAppointmentResource = createResource({
	url: UPSERT_DRAFT_APPOINTMENT_ENDPOINT,
	auto: false,
});

const updateDraftAppointmentNotesResource = createResource({
	url: UPDATE_DRAFT_APPOINTMENT_NOTES_ENDPOINT,
	auto: false,
});

const upsertDraftCoupleAppointmentsResource = createResource({
	url: UPSERT_DRAFT_COUPLE_APPOINTMENTS_ENDPOINT,
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

export async function upsertDraftCoupleAppointmentsApi({ bookingId, coupleAssignment }) {
	const response = await upsertDraftCoupleAppointmentsResource.fetch({
		booking_id: bookingId,
		couple_assignment: JSON.stringify(coupleAssignment || {}),
	});
	return unwrapPayload(response ?? upsertDraftCoupleAppointmentsResource.data);
}

export {
	UPSERT_DRAFT_APPOINTMENT_ENDPOINT,
	UPSERT_DRAFT_COUPLE_APPOINTMENTS_ENDPOINT,
	UPDATE_DRAFT_APPOINTMENT_NOTES_ENDPOINT,
};
