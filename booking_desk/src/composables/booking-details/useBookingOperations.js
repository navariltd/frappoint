import { useRouter } from "vue-router";

export function useBookingOperations() {
	const router = useRouter();

	const openAppointment = (appointment, booking) => {
		router.push({
			name: "AppointmentDetails",
			params: { appointmentId: appointment.appointmentId },
			query: booking?.bookingId ? { bookingId: booking.bookingId } : undefined,
		});
	};

	const addAppointment = (booking) => {
		router.push({ name: "GuestAssignment", query: { booking_id: booking.bookingId } });
	};

	const collectPayment = (booking) => {
		router.push({ name: "Checkout", query: { booking_id: booking.bookingId } });
	};

	const rescheduleBooking = (booking) => {
		router.push({ name: "GuestAssignment", query: { booking_id: booking.bookingId } });
	};

	const cancelBooking = (booking) => {
		return booking;
	};

	const rescheduleAppointment = (appointment, booking) => {
		openAppointment(appointment, booking);
	};

	const cancelAppointment = (appointment, booking) => {
		return { appointment, booking };
	};

	return {
		openAppointment,
		addAppointment,
		collectPayment,
		rescheduleBooking,
		cancelBooking,
		rescheduleAppointment,
		cancelAppointment,
	};
}
