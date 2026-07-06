import { createDraftServiceBookingApi, getDraftServiceBookingApi } from "@/api/serviceBooking.api";
import { upsertDraftServiceAppointmentApi } from "@/api/serviceAppointment.api";

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
	currency: payload?.currency || "KES",
	subtotal: Number(payload?.subtotal || 0),
	grandTotal: Number(payload?.grandTotal || 0),
	totalGuests: Number(payload?.totalGuests || 0),
	items: Array.isArray(payload?.items) ? payload.items : [],
	appointments: Array.isArray(payload?.appointments) ? payload.appointments : [],
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

export async function createDraftServiceBooking({ customer, customerSummary, cartItems }) {
	try {
		const customerPayload = buildCustomerPayload({ customer, customerSummary });
		const itemsPayload = buildDraftBookingItems(cartItems);
		const response = await createDraftServiceBookingApi({
			customer: customerPayload,
			items: itemsPayload,
		});
		return normalizeDraftBooking(response, {
			cartItems,
			customer: customerPayload,
		});
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Draft booking could not be created. Please try again.")
		);
	}
}

export async function reloadDraftServiceBooking({ bookingId, cartItems, customer }) {
	try {
		const response = await getDraftServiceBookingApi(bookingId);
		return normalizeDraftBooking(response, { cartItems, customer });
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
