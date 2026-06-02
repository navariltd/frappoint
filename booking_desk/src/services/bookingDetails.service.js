import { fetchBookingDetailsApi } from "@/api/bookingDetails.api";
import { createEmptyBookingDetails } from "@/types/booking-details";

function currencyAmount(value) {
	return Number(value || 0);
}

function normalizeAppointment(appointment) {
	return {
		id: appointment.name,
		appointmentId: appointment.name,
		serviceType: appointment.serviceType || "Service",
		provider: appointment.provider || "Unassigned",
		date: appointment.date || "",
		startTime: appointment.startTime || "",
		endTime: appointment.endTime || "",
		status: appointment.status || "Open",
		paymentStatus: appointment.paymentStatus || "Unpaid",
		totalAmount: currencyAmount(appointment.totalAmount),
		outstandingAmount: currencyAmount(appointment.outstandingAmount),
		fullName: appointment.fullName || "Guest",
		email: appointment.email || "",
		mobileNo: appointment.mobileNo || "",
		slotIds: [],
	};
}

function buildAlerts(booking) {
	const alerts = [];
	if (booking.outstandingAmount > 0) {
		alerts.push({
			id: "outstanding",
			severity: "warning",
			label: "Outstanding balance",
			message: `${booking.currency} ${booking.outstandingAmount.toFixed(2)} remains unpaid.`,
		});
	}
	const delayed = booking.appointments.filter(
		(appointment) => String(appointment.status || "").toLowerCase() === "checked in"
	);
	if (delayed.length) {
		alerts.push({
			id: "checkedin",
			severity: "info",
			label: "Checked-in appointments",
			message: `${delayed.length} appointment(s) are currently checked in.`,
		});
	}
	return alerts;
}

export async function fetchBookingDetails(bookingId) {
	const payload = await fetchBookingDetailsApi(bookingId);
	const booking = payload || createEmptyBookingDetails();
	const appointments = (booking.appointments || []).map(normalizeAppointment);
	const totalAmount = currencyAmount(booking.grandTotal);
	const outstandingAmount = currencyAmount(booking.outstandingAmount);
	const paidAmount = Math.max(0, totalAmount - outstandingAmount);

	return {
		id: booking.id || booking.bookingId || booking.booking_id || booking.name,
		bookingId:
			booking.name || booking.bookingId || booking.id || booking.booking_id || bookingId,
		status: booking.status || "Draft",
		paymentStatus: booking.paymentStatus || (outstandingAmount > 0 ? "Unpaid" : "Paid"),
		customer: booking.customer || "",
		customerName: booking.customerName || booking.fullName || "Walk-in Customer",
		email: booking.email || "",
		mobileNo: booking.mobileNo || "",
		currency: booking.currency || "KES",
		bookingDate: booking.bookingDate || "",
		appointmentCount: Number(booking.appointmentCount || appointments.length),
		totalGuests: Number(booking.totalGuests || 0),
		subtotal: currencyAmount(booking.subtotal),
		grandTotal: totalAmount,
		paidAmount,
		outstandingAmount,
		items: booking.items || [],
		appointments,
		alerts: buildAlerts({
			...booking,
			appointments,
			outstandingAmount,
			currency: booking.currency || "KES",
		}),
	};
}
