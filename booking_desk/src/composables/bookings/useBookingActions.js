import { useRouter } from "vue-router";

export function useBookingActions() {
	const router = useRouter();

	const openBooking = (booking) => {
		router.push({
			name: "BookingDetails",
			params: { bookingId: booking.bookingId },
			query: { source: "workspace" },
		});
	};

	const collectPayment = (booking) => {
		router.push({ name: "Checkout", query: { booking_id: booking.bookingId } });
	};

	const checkIn = (booking) => {
		openBooking(booking);
	};

	const reschedule = (booking) => {
		openBooking(booking);
	};

	const cancelBooking = (booking) => {
		openBooking(booking);
	};

	return {
		openBooking,
		collectPayment,
		checkIn,
		reschedule,
		cancelBooking,
	};
}
