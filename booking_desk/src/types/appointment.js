export function createDraftAppointmentSnapshot() {
	return {
		appointmentId: "",
		guestKey: "",
		serviceKey: "",
		serviceId: "",
		date: "",
		slot: null,
		guest: {
			fullName: "",
			email: "",
			mobileNo: "",
		},
	};
}
