import { fetchBookingsWorkspaceApi } from "@/api/bookings.api";

function toCurrencyAmount(value) {
	return Number(value || 0);
}

function toPreviewAppointment(appointment) {
	return {
		id: appointment.name,
		serviceType: appointment.serviceType || "Service",
		provider: appointment.provider || "Unassigned",
		date: appointment.date || "",
		startTime: appointment.startTime || "",
		status: appointment.status || "Open",
		coupleAppointmentId:
			appointment.coupleAppointmentId || appointment.couple_appointment_id || "",
		isPrimaryInCouple: Boolean(
			appointment.isPrimaryInCouple ?? appointment.is_primary_in_couple
		),
		isCouple: Boolean(
			appointment.isCouple ||
				appointment.is_couple ||
				appointment.coupleAppointmentId ||
				appointment.couple_appointment_id
		),
	};
}

function deriveUpcomingAppointment(appointments) {
	if (!appointments.length) {
		return null;
	}
	const sorted = [...appointments].sort((a, b) => {
		const aDate = `${a.date || ""} ${a.startTime || "00:00"}`;
		const bDate = `${b.date || ""} ${b.startTime || "00:00"}`;
		return aDate.localeCompare(bDate);
	});
	return sorted[0];
}

export function normalizeServiceBooking(raw) {
	const appointments = (raw.appointments || []).map(toPreviewAppointment);
	const upcomingAppointment = deriveUpcomingAppointment(appointments);

	return {
		id: raw.name,
		bookingId: raw.name,
		status: raw.status || "Draft",
		paymentStatus: raw.paymentStatus || "Unpaid",
		customer: raw.customer || "",
		customerName: raw.fullName || "Walk-in Customer",
		email: raw.email || "",
		mobileNo: raw.mobileNo || "",
		currency: raw.currency || "KES",
		bookingDate: raw.bookingDate || "",
		totalGuests: Number(raw.totalGuests || 0),
		appointmentCount: Number(raw.appointmentCount || appointments.length),
		grandTotal: toCurrencyAmount(raw.grandTotal),
		outstandingAmount: toCurrencyAmount(raw.outstandingAmount),
		upcomingAppointment,
		appointments,
		isCouple: Boolean(
			raw.isCouple || raw.is_couple || appointments.some((row) => row.isCouple)
		),
		items: raw.items || [],
	};
}

export async function fetchBookingsWorkspace(params) {
	const payload = await fetchBookingsWorkspaceApi(params);
	const bookings = (payload?.bookings || []).map(normalizeServiceBooking);

	return {
		bookings,
		page: Number(payload?.page || params?.page || 1),
		pageSize: Number(payload?.pageSize || params?.pageSize || 20),
		hasMore: Boolean(payload?.hasMore),
	};
}
