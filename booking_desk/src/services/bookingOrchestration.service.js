import { createDraftServiceBookingApi, getDraftServiceBookingApi } from "@/api/serviceBooking.api";
import {
	updateDraftServiceAppointmentNotesApi,
	upsertDraftCoupleAppointmentsApi,
	upsertDraftServiceAppointmentApi,
} from "@/api/serviceAppointment.api";

const extractErrorMessage = (error, fallback) => {
	const candidate =
		error?.messages?.join(" ") || error?.message || error?.exc || error?._server_messages;

	if (!candidate) {
		return fallback;
	}

	const message = String(candidate);
	if (message.includes("slot") && message.includes("available")) {
		return "Slot no longer available. Please choose another slot.";
	}
	if (
		message.includes("cannot provide service type") ||
		(message.includes("Provider") && message.includes("unavailable"))
	) {
		return "Provider already assigned or unavailable for this slot.";
	}
	if (message.includes("Booking reference is required")) {
		return "Create a draft booking before reserving appointments.";
	}
	if (message.includes("Guest full name is required")) {
		return "Guest details are required before reserving the slot.";
	}

	return message;
};

const normalizeDraftBooking = (payload, snapshots = {}) => ({
	id: payload?.name || "",
	name: payload?.name || "",
	status: payload?.status || "Draft",
	customerId: payload?.customer || snapshots.customer?.customer || "",
	fullName: payload?.fullName || snapshots.customer?.fullName || "",
	email: payload?.email || snapshots.customer?.email || "",
	mobileNo: payload?.mobileNo || snapshots.customer?.mobileNo || "",
	bookedBy: payload?.bookedBy || payload?.booked_by || snapshots.bookedBy || "",
	currency: payload?.currency || "KES",
	subtotal: Number(payload?.subtotal || 0),
	grandTotal: Number(payload?.grandTotal || 0),
	totalGuests: Number(payload?.totalGuests || 0),
	items: Array.isArray(payload?.items) ? payload.items : [],
	appointments: Array.isArray(payload?.appointments) ? payload.appointments : [],
	// Before a slot is reserved the server has no linked appointments from which
	// to infer couple mode. Preserve the persisted workflow intent across reloads.
	isCouple: Boolean(snapshots.isCouple || payload?.isCouple || payload?.is_couple),
	coupleServiceKeys:
		payload?.coupleServiceKeys ||
		payload?.couple_service_keys ||
		snapshots.coupleServiceKeys ||
		[],
	cartItemsSnapshot: snapshots.cartItems || [],
	customerSnapshot: snapshots.customer || null,
});

const buildCustomerPayload = ({ customer, customerSummary }) => ({
	customer: customer?.id || "",
	fullName: customerSummary?.name || customer?.name || "",
	email: customerSummary?.email && customerSummary.email !== "-" ? customerSummary.email : "",
	mobileNo: customerSummary?.phone && customerSummary.phone !== "-" ? customerSummary.phone : "",
});

const buildDraftBookingItems = (cartItems = []) =>
	cartItems.map((item) => ({
		serviceId: item.serviceId,
		serviceType: item.serviceId,
		serviceName: item.name,
		quantity: Number(item.quantity || 1),
		priceId: item.packageId || null,
		packageId: item.packageId || null,
		packageName: item.packageName || "Default",
		pricingModel: item.pricingModel || "Per Guest",
		rate: Number(item.price || 0),
		price: Number(item.price || 0),
		currency: item.currency || "KES",
		duration: Number(item.duration || 0),
		totalAmount: Number(item.price || 0) * Number(item.quantity || 1),
	}));

const buildDraftAppointmentPayload = ({ service, guest, date, slot }) => ({
	serviceId: service.serviceId,
	serviceType: service.serviceId,
	serviceKey: service.serviceKey,
	serviceName: service.serviceName,
	service: {
		serviceId: service.serviceId,
		serviceType: service.serviceId,
		serviceKey: service.serviceKey,
		serviceName: service.serviceName,
		pricingModel: service.pricingModel || "",
		packageId: service.packageId || null,
		packageName: service.packageName || "Default",
		priceId: service.packageId || null,
		price: Number(service.price || 0),
		currency: service.currency || "KES",
		duration: Number(service.duration || 0),
	},
	packageId: service.packageId || null,
	packageName: service.packageName || "Default",
	priceId: service.packageId || null,
	pricingModel: service.pricingModel || "",
	price: Number(service.price || 0),
	currency: service.currency || "KES",
	duration: Number(service.duration || 0),
	date,
	guest: {
		fullName: guest.fullName,
		email: guest.email || "",
		mobileNo: guest.mobileNo || "",
		providerGender: guest.providerGender || "",
		providerPreference: guest.providerPreference || "",
		notes: guest.notes || "",
	},
	slot: {
		id: slot.id,
		startTime: slot.startTime,
		endTime: slot.endTime,
		provider: guest.providerPreference || "",
		providerSummary: slot.providerSummary,
		slotIds:
			slot.providers?.find((provider) => provider.provider === guest.providerPreference)
				?.slotIds ||
			(!guest.providerPreference && slot.providers?.length === 1
				? slot.providers[0]?.slotIds || []
				: []),
		providers: slot.providers || [],
	},
});

const buildCoupleServicePayload = (service = {}) => ({
	service_id: service.serviceId,
	service_type: service.serviceId,
	service_key: service.serviceKey,
	service_name: service.serviceName,
	pricing_model: service.pricingModel || "",
	package_id: service.packageId || null,
	package_name: service.packageName || "Default",
	price_id: service.packageId || null,
	price: Number(service.price || 0),
	currency: service.currency || "KES",
	duration: Number(service.duration || 0),
});

const buildCoupleGuestPayload = (guest = {}) => ({
	guest_key: guest.guestKey,
	appointment_id: guest.appointmentId || undefined,
	full_name: guest.fullName,
	email: guest.email || "",
	mobile_no: guest.mobileNo || "",
	provider_gender: guest.providerGender || "",
	provider_preference: guest.providerPreference || "",
	notes: guest.notes || "",
});

const buildCoupleSlotLeg = (leg = {}) => ({
	provider: leg.provider || "",
	provider_name: leg.providerName || leg.provider || "",
	service_unit: leg.serviceUnit || null,
	service_unit_name: leg.serviceUnitName || null,
	start_time: leg.startTime || "",
	end_time: leg.endTime || "",
	duration: Number(leg.duration || 0),
	buffer_before: Number(leg.bufferBefore || 0),
	buffer_after: Number(leg.bufferAfter || 0),
	slot_ids: Array.isArray(leg.slotIds) ? leg.slotIds : [],
});

const buildCoupleAssignmentPayload = ({ primary, secondary, slot }) => {
	const guest1 = buildCoupleGuestPayload(primary.guest);
	const guest2 = buildCoupleGuestPayload(secondary.guest);
	const service1 = buildCoupleServicePayload(primary.service);
	const service2 = buildCoupleServicePayload(secondary.service);
	const slotGuest1 = buildCoupleSlotLeg(slot.guest1);
	const slotGuest2 = buildCoupleSlotLeg(slot.guest2);

	return {
		is_couple: 1,
		guest_1: guest1,
		guest_2: guest2,
		service_type_1: primary.service.serviceId,
		service_type_2: secondary.service.serviceId,
		duration_1: Number(primary.service.duration || 0),
		duration_2: Number(secondary.service.duration || 0),
		service_1: service1,
		service_2: service2,
		preferred_provider_1: primary.guest.providerPreference || "",
		preferred_provider_2: secondary.guest.providerPreference || "",
		appointment_id_1: primary.guest.appointmentId || undefined,
		appointment_id_2: secondary.guest.appointmentId || undefined,
		selected_time_slot: {
			id: slot.id,
			candidate_id: slot.candidateId || slot.id,
			date: slot.date,
			start_time: slot.startTime,
			provider_1: slotGuest1.provider,
			provider_2: slotGuest2.provider,
			guest_1: slotGuest1,
			guest_2: slotGuest2,
		},
	};
};

export async function createDraftServiceBooking({
	customer,
	customerSummary,
	cartItems,
	bookedBy,
	isCouple = false,
	coupleServiceKeys = [],
}) {
	try {
		const customerPayload = buildCustomerPayload({ customer, customerSummary });
		const itemsPayload = buildDraftBookingItems(cartItems);
		const response = await createDraftServiceBookingApi({
			customer: customerPayload,
			items: itemsPayload,
			bookedBy,
			isCouple,
		});
		return normalizeDraftBooking(response, {
			cartItems,
			customer: customerPayload,
			bookedBy,
			isCouple,
			coupleServiceKeys,
		});
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Draft booking could not be created. Please try again.")
		);
	}
}

export async function reloadDraftServiceBooking({
	bookingId,
	cartItems,
	customer,
	isCouple,
	coupleServiceKeys,
}) {
	try {
		const response = await getDraftServiceBookingApi(bookingId);
		return normalizeDraftBooking(response, {
			cartItems,
			customer,
			isCouple,
			coupleServiceKeys,
		});
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Draft booking could not be loaded right now.")
		);
	}
}

export async function upsertDraftServiceAppointment({
	bookingId,
	appointmentId,
	service,
	guest,
	date,
	slot,
}) {
	try {
		const response = await upsertDraftServiceAppointmentApi({
			bookingId,
			appointmentId,
			assignment: buildDraftAppointmentPayload({ service, guest, date, slot }),
		});

		return {
			booking: normalizeDraftBooking(response?.booking),
			appointment: response?.appointment || null,
		};
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Appointment could not be reserved. Please try again.")
		);
	}
}

export async function upsertDraftCoupleAppointments({ bookingId, primary, secondary, slot }) {
	try {
		const response = await upsertDraftCoupleAppointmentsApi({
			bookingId,
			coupleAssignment: buildCoupleAssignmentPayload({ primary, secondary, slot }),
		});
		const appointments =
			response?.appointments ||
			[
				response?.primaryAppointment || response?.primary_appointment,
				response?.secondaryAppointment || response?.secondary_appointment,
			].filter(Boolean);

		return {
			booking: normalizeDraftBooking(response?.booking),
			appointments,
			primaryAppointment:
				response?.primaryAppointment ||
				response?.primary_appointment ||
				appointments[0] ||
				null,
			secondaryAppointment:
				response?.secondaryAppointment ||
				response?.secondary_appointment ||
				appointments[1] ||
				null,
			coupleAppointmentId:
				response?.coupleAppointmentId || response?.couple_appointment_id || "",
		};
	} catch (error) {
		throw new Error(
			extractErrorMessage(
				error,
				"Both appointments could not be reserved together. Please choose another slot."
			)
		);
	}
}

export async function updateDraftServiceAppointmentNotes({ appointmentId, notes }) {
	try {
		return await updateDraftServiceAppointmentNotesApi({ appointmentId, notes });
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Appointment notes could not be saved. Please try again.")
		);
	}
}
