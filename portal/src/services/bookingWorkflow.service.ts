import type { CartItem } from "@/stores/bookingCart.store";
import {
	checkSlotAvailabilityApi,
	createDraftServiceBookingApi,
	fetchAvailableDatesApi,
	fetchAvailableSlotsApi,
	getLoggedInCustomerApi,
	getDraftServiceBookingApi,
	upsertDraftServiceAppointmentApi,
} from "@/api/bookingWorkflow.api";

export interface AvailableDate {
	date: string;
	label: string;
}

export interface AvailableSlotProvider {
	provider: string;
	providerName: string;
	serviceUnit: string | null;
	serviceUnitName: string | null;
	slotIds: string[];
}

export interface AvailableSlot {
	id: string;
	date: string;
	startTime: string;
	endTime: string;
	duration: number;
	availability: "available" | "partial" | "unavailable";
	providers: AvailableSlotProvider[];
	providerSummary: string;
	slotIds: string[];
}

export interface LoggedInCustomerProfile {
	customer: string;
	contact: {
		contact_display?: string;
		contact_email?: string;
		contact_phone?: string;
	};
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
	weekday: "short",
	month: "short",
	day: "numeric",
});

const toNumber = (value: unknown, fallback = 0) => {
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : fallback;
};

const extractErrorMessage = (error: any, fallback: string) => {
	const candidate =
		error?.messages?.join(" ") || error?.message || error?.exc || error?._server_messages;
	if (!candidate) return fallback;

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

const formatDateLabel = (dateValue: string) => {
	const parsed = new Date(`${dateValue}T00:00:00`);
	if (Number.isNaN(parsed.getTime())) return String(dateValue);
	return dateFormatter.format(parsed);
};

const toProviderSummary = (providers: AvailableSlotProvider[]) => {
	if (!providers.length) return "No provider";
	if (providers.length === 1) return providers[0].providerName;
	return `${providers.length} providers`;
};

const normalizeProviders = (providers: any[] = []): AvailableSlotProvider[] => {
	return providers.map((provider) => ({
		provider: provider.provider || "",
		providerName: provider.provider_name || "Any available",
		serviceUnit: provider.service_unit || null,
		serviceUnitName: provider.service_unit_name || null,
		slotIds: Array.isArray(provider.slot_ids) ? provider.slot_ids : [],
	}));
};

const normalizeSlot = (slot: any, date: string): AvailableSlot => {
	const providers = normalizeProviders(slot.providers || []);
	const slotIds = providers.flatMap((provider) => provider.slotIds);
	return {
		id: `${date}:${slot.start_time}-${slot.end_time}`,
		date,
		startTime: slot.start_time,
		endTime: slot.end_time,
		duration: toNumber(slot.duration),
		availability: providers.length > 1 ? "partial" : providers.length ? "available" : "unavailable",
		providers,
		providerSummary: toProviderSummary(providers),
		slotIds,
	};
};

const normalizeDraftBooking = (payload: any, snapshots: any = {}) => ({
	id: payload?.name || "",
	name: payload?.name || "",
	status: payload?.status || "Draft",
	customerId: payload?.customer || snapshots.customer?.customer || "",
	fullName: payload?.fullName || snapshots.customer?.fullName || "",
	email: payload?.email || snapshots.customer?.email || "",
	mobileNo: payload?.mobileNo || snapshots.customer?.mobileNo || "",
	currency: payload?.currency || snapshots.currency || "KES",
	subtotal: Number(payload?.subtotal || 0),
	grandTotal: Number(payload?.grandTotal || 0),
	totalGuests: Number(payload?.totalGuests || 0),
	items: Array.isArray(payload?.items) ? payload.items : [],
	appointments: Array.isArray(payload?.appointments) ? payload.appointments : [],
	cartItemsSnapshot: snapshots.cartItems || [],
	customerSnapshot: snapshots.customer || null,
});

const buildDraftBookingItems = (cartItems: CartItem[]) =>
	cartItems.map((item) => ({
		serviceId: item.service_type,
		serviceType: item.service_type,
		serviceName: item.service_name,
		quantity: Number(item.quantity || 1),
		priceId: item.metadata?.price_id || item.package_name,
		packageId: item.metadata?.package_id || item.package_name,
		packageName: item.package_name || "Default",
		pricingModel: item.metadata?.pricing_model || "Per Guest",
		rate: Number(item.price || 0),
		price: Number(item.price || 0),
		currency: item.currency || "KES",
		duration: Number(item.duration_minutes || 0),
		totalAmount: Number(item.price || 0) * Number(item.quantity || 1),
	}));

export async function createDraftServiceBooking(params: {
	customer: { customer?: string; fullName?: string; email?: string; mobileNo?: string };
	cartItems: CartItem[];
}) {
	try {
		const customerPayload = {
			customer: params.customer.customer || "",
			fullName: params.customer.fullName || "",
			email: params.customer.email || "",
			mobileNo: params.customer.mobileNo || "",
		};
		const itemsPayload = buildDraftBookingItems(params.cartItems);
		const response = await createDraftServiceBookingApi({
			customer: customerPayload,
			items: itemsPayload,
		});
		return normalizeDraftBooking(response, {
			cartItems: params.cartItems,
			customer: customerPayload,
			currency: params.cartItems[0]?.currency,
		});
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Draft booking could not be created. Please try again.")
		);
	}
}

export async function reloadDraftServiceBooking(params: {
	bookingId: string;
	cartItems: CartItem[];
	customer: { customer?: string; fullName?: string; email?: string; mobileNo?: string };
}) {
	try {
		const response = await getDraftServiceBookingApi(params.bookingId);
		return normalizeDraftBooking(response, {
			cartItems: params.cartItems,
			customer: params.customer,
			currency: params.cartItems[0]?.currency,
		});
	} catch (error) {
		throw new Error(
			extractErrorMessage(error, "Draft booking could not be loaded right now.")
		);
	}
}

export async function fetchNormalizedAvailableDates(params: {
	serviceType: string;
	duration: number;
	provider?: string;
}) {
	const response = await fetchAvailableDatesApi(params);
	const rows = Array.isArray(response) ? response : [];
	return rows.map((date) => ({
		date,
		label: formatDateLabel(date),
	})) as AvailableDate[];
}

export async function fetchNormalizedAvailableSlots(params: {
	serviceType: string;
	duration: number;
	provider?: string;
	date: string;
}) {
	const response = await fetchAvailableSlotsApi(params);
	const dateGroups = Array.isArray(response) ? response : [];
	const targetGroup = dateGroups.find((group: any) => String(group.date) === String(params.date));
	const rawSlots = targetGroup?.slots || [];
	return rawSlots.map((slot: any) => normalizeSlot(slot, params.date));
}

export async function validateSlotAvailability(slotIds: string[]) {
	if (!slotIds.length) {
		return { available: false, unavailableSlots: [] as string[] };
	}
	const response = await checkSlotAvailabilityApi(slotIds);
	return {
		available: Boolean(response?.available),
		unavailableSlots: Array.isArray(response?.unavailable_slots)
			? response.unavailable_slots
			: [],
	};
}

export async function upsertDraftServiceAppointment(params: {
	bookingId: string;
	appointmentId?: string;
	service: {
		serviceKey: string;
		serviceId: string;
		serviceName: string;
		packageName: string;
		packageId?: string;
		price: number;
		currency: string;
		duration: number;
	};
	guest: {
		fullName: string;
		email?: string;
		mobileNo?: string;
		notes?: string;
	};
	date: string;
	slot: AvailableSlot;
}) {
	try {
		const assignment = {
			serviceId: params.service.serviceId,
			serviceType: params.service.serviceId,
			serviceKey: params.service.serviceKey,
			serviceName: params.service.serviceName,
			service: {
				serviceId: params.service.serviceId,
				serviceType: params.service.serviceId,
				serviceKey: params.service.serviceKey,
				serviceName: params.service.serviceName,
				pricingModel: "Per Guest",
				packageId: params.service.packageId || null,
				packageName: params.service.packageName || "Default",
				priceId: params.service.packageId || null,
				price: Number(params.service.price || 0),
				currency: params.service.currency || "KES",
				duration: Number(params.service.duration || 0),
			},
			packageId: params.service.packageId || null,
			packageName: params.service.packageName || "Default",
			priceId: params.service.packageId || null,
			pricingModel: "Per Guest",
			price: Number(params.service.price || 0),
			currency: params.service.currency || "KES",
			duration: Number(params.service.duration || 0),
			date: params.date,
			guest: {
				fullName: params.guest.fullName,
				email: params.guest.email || "",
				mobileNo: params.guest.mobileNo || "",
				notes: params.guest.notes || "",
			},
			slot: {
				id: params.slot.id,
				startTime: params.slot.startTime,
				endTime: params.slot.endTime,
				provider: params.slot.providers?.[0]?.provider || "",
				providerSummary: params.slot.providerSummary,
				slotIds: params.slot.slotIds || [],
				providers: params.slot.providers || [],
			},
		};

		const response = await upsertDraftServiceAppointmentApi({
			bookingId: params.bookingId,
			appointmentId: params.appointmentId,
			assignment,
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

export async function resolveLoggedInCustomerProfile(): Promise<LoggedInCustomerProfile | null> {
	try {
		const response = await getLoggedInCustomerApi();
		if (!response?.customer) {
			return null;
		}
		return {
			customer: response.customer,
			contact: response.contact || {},
		};
	} catch (error) {
		throw new Error(
			extractErrorMessage(
				error,
				"Unable to resolve customer profile for this portal user."
			)
		);
	}
}
