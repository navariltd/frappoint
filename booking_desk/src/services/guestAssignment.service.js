const makeGuestKey = (serviceKey, sequence) => `${serviceKey}:guest:${sequence}`;

const toNumber = (value, fallback = 0) => {
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : fallback;
};

export function buildAssignmentsFromCart(
	cartItems = [],
	selectedCustomer = null,
	appointmentsByGuestKey = {}
) {
	return cartItems.map((item) => {
		const quantity = Math.max(1, toNumber(item.quantity, 1));
		const guests = Array.from({ length: quantity }).map((_, index) => {
			const sequence = index + 1;
			const guestKey = makeGuestKey(item.cartKey || item.serviceId, sequence);
			const persistedAppointment = appointmentsByGuestKey[guestKey] || null;
			const useSelectedCustomer = Boolean(selectedCustomer && sequence === 1);

			return {
				guestKey,
				sequence,
				appointmentId: persistedAppointment?.appointmentId || "",
				customerId: useSelectedCustomer ? selectedCustomer.id : "",
				fullName:
					persistedAppointment?.guest?.fullName ||
					(useSelectedCustomer ? selectedCustomer.name : ""),
				email: persistedAppointment?.guest?.email || "",
				mobileNo: persistedAppointment?.guest?.mobileNo || "",
				notes: persistedAppointment?.guest?.notes || "",
				providerGender: persistedAppointment?.guest?.providerGender || "",
				providerPreference: persistedAppointment?.guest?.providerPreference || "",
				isInlineGuest:
					Boolean(persistedAppointment?.guest?.fullName) || !useSelectedCustomer,
				isComplete: Boolean(persistedAppointment?.slot && persistedAppointment?.date),
				date: persistedAppointment?.date || "",
				slot: persistedAppointment?.slot || null,
				availableDates: [],
				availableSlots: [],
			};
		});

		return {
			serviceKey: item.cartKey || item.serviceId,
			serviceId: item.serviceId,
			serviceName: item.name,
			packageName: item.packageName || "Default",
			quantity,
			duration: toNumber(item.duration),
			price: toNumber(item.price),
			packageId: item.packageId || null,
			currency: item.currency || "KES",
			providerOptions: Array.isArray(item.providers) ? item.providers : [],
			guests,
		};
	});
}

export function getAssignmentProgress(assignments = []) {
	const totalGuests = assignments.reduce((sum, item) => sum + item.guests.length, 0);
	const completedGuests = assignments.reduce(
		(sum, item) => sum + item.guests.filter((guest) => guest.isComplete).length,
		0
	);
	const percent = totalGuests ? Math.round((completedGuests / totalGuests) * 100) : 0;

	return {
		totalGuests,
		completedGuests,
		percent,
	};
}

export function summarizeAssignments(assignments = []) {
	return assignments
		.flatMap((service) =>
			service.guests.map((guest) => ({
				serviceKey: service.serviceKey,
				serviceName: service.serviceName,
				price: service.price,
				currency: service.currency,
				guestKey: guest.guestKey,
				guestName: guest.fullName || `Guest ${guest.coupleSequence || guest.sequence}`,
				isComplete: guest.isComplete,
				date: guest.date,
				slotLabel: guest.slot ? `${guest.slot.startTime} - ${guest.slot.endTime}` : "",
				providerLabel: guest.slot?.providerSummary || "",
				coupleSequence: guest.coupleSequence,
			}))
		)
		.sort(
			(a, b) =>
				Number(a.coupleSequence || Number.MAX_SAFE_INTEGER) -
				Number(b.coupleSequence || Number.MAX_SAFE_INTEGER)
		);
}

export function buildValidationIssues(assignments = [], { isCouple = false } = {}) {
	const issues = [];
	const slotUsage = new Map();
	const guests = assignments.flatMap((service) => service.guests);

	if (isCouple && guests.length !== 2) {
		issues.push("Couple bookings require exactly two guests and two services.");
	}

	assignments.forEach((service) => {
		if (service.guests.length > service.quantity) {
			issues.push(`${service.serviceName}: guest count exceeds service quantity.`);
		}

		service.guests.forEach((guest) => {
			const guestNumber = guest.coupleSequence || guest.sequence;
			if (!guest.fullName) {
				issues.push(`${service.serviceName} - Guest ${guestNumber}: guest is required.`);
			}
			if (!guest.date) {
				issues.push(`${service.serviceName} - Guest ${guestNumber}: date is required.`);
			}
			if (!guest.slot) {
				issues.push(`${service.serviceName} - Guest ${guestNumber}: slot is required.`);
			}

			if (guest.slot && !isCouple) {
				const slotKey = `${guest.date}:${guest.slot.startTime}:${guest.slot.providerSummary}`;
				slotUsage.set(slotKey, (slotUsage.get(slotKey) || 0) + 1);
			}
		});
	});

	if (!isCouple) {
		for (const [key, count] of slotUsage.entries()) {
			if (count > 1) {
				issues.push(`Duplicate slot conflict detected at ${key}.`);
			}
		}
	}

	if (isCouple && guests.length === 2 && guests.every((guest) => guest.slot)) {
		const [guest1, guest2] = [...guests].sort(
			(a, b) => Number(a.coupleSequence || 0) - Number(b.coupleSequence || 0)
		);
		if (guest1.date !== guest2.date || guest1.slot.startTime !== guest2.slot.startTime) {
			issues.push("Both couple appointments must start together on the same date.");
		}
	}

	return Array.from(new Set(issues));
}
