import { createResource } from "frappe-ui";

const GET_APPOINTMENT_DETAILS_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_appointment_details";
const PERFORM_APPOINTMENT_ACTION_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.perform_appointment_action";

const appointmentDetailsResource = createResource({
	url: GET_APPOINTMENT_DETAILS_ENDPOINT,
	auto: false,
});

const appointmentActionResource = createResource({
	url: PERFORM_APPOINTMENT_ACTION_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function fetchAppointmentDetailsApi(appointmentId) {
	const response = await appointmentDetailsResource.fetch({ appointment_id: appointmentId });
	return unwrapPayload(response ?? appointmentDetailsResource.data);
}

export async function performAppointmentActionApi(payload) {
	const requestPayload = {
		appointment_id: payload.appointmentId,
		action: payload.action,
		new_appointment_date: payload.newAppointmentDate,
		new_start_time: payload.newStartTime,
		new_end_time: payload.newEndTime,
		new_provider: payload.newProvider,
		new_slot_ids: payload.newSlotIds,
		new_service_unit: payload.newServiceUnit,
		actual_start_time: payload.actualStartTime,
		actual_end_time: payload.actualEndTime,
		cancellation_reasons: payload.cancellationReasons,
		cancel_couple: payload.cancelCouple,
		couple_update: payload.coupleUpdate,
	};

	Object.keys(requestPayload).forEach((key) => {
		if (requestPayload[key] === undefined) {
			delete requestPayload[key];
		}
	});

	const response = await appointmentActionResource.fetch(requestPayload);

	return unwrapPayload(response ?? appointmentActionResource.data);
}
