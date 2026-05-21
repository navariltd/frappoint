import {
	getCheckoutSummaryApi,
	getOnlineGatewaysApi,
	createPaymentLinkApi,
} from "@/api/checkout.api";

// ----- Types -----

export interface CheckoutBookingSummary {
	name: string;
	status: string;
	customer: string;
	fullName: string;
	email: string;
	mobileNo: string;
	currency: string;
	subtotal: number;
	grandTotal: number;
	outstandingAmount: number;
	items: CheckoutBookingItem[];
	appointments: CheckoutAppointment[];
}

export interface CheckoutBookingItem {
	serviceType: string;
	pricingModel: string;
	qty: number;
	totalAmount: number;
}

export interface CheckoutAppointment {
	name: string;
	appointmentType: string;
	guestName: string;
	date: string;
	startTime: string;
	endTime: string;
	status: string;
	price: number;
	currency: string;
}

export interface CheckoutPaymentSummary {
	referenceDoctype: string;
	referenceDocname: string;
	currency: string;
	totalAmount: number;
	paidAmount: number;
	outstandingAmount: number;
	minimumDue: number;
	depositPercent: number;
}

export interface CheckoutSummary {
	booking: CheckoutBookingSummary;
	payment: CheckoutPaymentSummary;
}

export interface OnlineGateway {
	id: string;
	name: string;
	label: string;
	gateway: string;
	providerType: string;
	capabilities: string[];
	details: string;
}

export interface PaymentLinkResult {
	paymentUrl?: string;
	url?: string;
	redirectUrl?: string;
	status?: string;
	message?: string;
	checkout?: CheckoutSummary;
	raw?: any;
}

// ----- Empty state factories -----

export function createEmptyCheckoutSummary(): CheckoutSummary {
	return {
		booking: {
			name: "",
			status: "Draft",
			customer: "",
			fullName: "",
			email: "",
			mobileNo: "",
			currency: "KES",
			subtotal: 0,
			grandTotal: 0,
			outstandingAmount: 0,
			items: [],
			appointments: [],
		},
		payment: {
			referenceDoctype: "Service Booking",
			referenceDocname: "",
			currency: "KES",
			totalAmount: 0,
			paidAmount: 0,
			outstandingAmount: 0,
			minimumDue: 0,
			depositPercent: 100,
		},
	};
}

// ----- Normalizers (ported from booking_desk services) -----

function normalizeAppointment(raw: any): CheckoutAppointment {
	return {
		name: raw?.name || "",
		appointmentType: raw?.appointment_type || raw?.appointmentType || "",
		guestName: raw?.guest_full_name || raw?.guestName || raw?.full_name || "",
		date: raw?.appointment_date || raw?.date || "",
		startTime: raw?.start_time || raw?.startTime || "",
		endTime: raw?.end_time || raw?.endTime || "",
		status: raw?.status || "",
		price: Number(raw?.price || raw?.rate || 0),
		currency: raw?.currency || "",
	};
}

function normalizeBookingItem(raw: any): CheckoutBookingItem {
	return {
		serviceType: raw?.service_type || raw?.serviceType || "",
		pricingModel: raw?.pricing_model || raw?.pricingModel || "",
		qty: Number(raw?.qty || 1),
		totalAmount: Number(raw?.total_amount || raw?.totalAmount || raw?.amount || 0),
	};
}

export function normalizeCheckoutSummary(payload: any): CheckoutSummary {
	const empty = createEmptyCheckoutSummary();
	if (!payload) return empty;

	const bookingRaw = payload.booking || {};
	const paymentRaw = payload.payment || {};

	return {
		booking: {
			name: bookingRaw.name || "",
			status: bookingRaw.status || "Draft",
			customer: bookingRaw.customer || "",
			fullName: bookingRaw.full_name || bookingRaw.fullName || "",
			email: bookingRaw.email || "",
			mobileNo: bookingRaw.mobile_no || bookingRaw.mobileNo || "",
			currency: bookingRaw.currency || "KES",
			subtotal: Number(bookingRaw.subtotal || 0),
			grandTotal: Number(bookingRaw.grand_total || bookingRaw.grandTotal || 0),
			outstandingAmount: Number(
				bookingRaw.outstanding_amount || bookingRaw.outstandingAmount || 0
			),
			items: Array.isArray(bookingRaw.items)
				? bookingRaw.items.map(normalizeBookingItem)
				: [],
			appointments: Array.isArray(bookingRaw.appointments)
				? bookingRaw.appointments.map(normalizeAppointment)
				: [],
		},
		payment: {
			referenceDoctype: paymentRaw.reference_doctype || paymentRaw.referenceDoctype || "Service Booking",
			referenceDocname: paymentRaw.reference_docname || paymentRaw.referenceDocname || "",
			currency: paymentRaw.currency || bookingRaw.currency || "KES",
			totalAmount: Number(paymentRaw.total_amount || paymentRaw.totalAmount || 0),
			paidAmount: Number(paymentRaw.paid_amount || paymentRaw.paidAmount || 0),
			outstandingAmount: Number(
				paymentRaw.outstanding_amount || paymentRaw.outstandingAmount || 0
			),
			minimumDue: Number(paymentRaw.minimum_due || paymentRaw.minimumDue || 0),
			depositPercent: Number(paymentRaw.deposit_percent || paymentRaw.depositPercent || 100),
		},
	};
}

function inferGatewayProviderType(raw: any): string {
	if (raw.providerType) return raw.providerType;
	const label = String(raw.label || raw.gateway || "").toLowerCase();
	if (label.includes("mpesa") || label.includes("m-pesa")) return "mpesa";
	return "hosted";
}

function inferGatewayCapabilities(raw: any): string[] {
	if (Array.isArray(raw.capabilities) && raw.capabilities.length) return raw.capabilities;
	const label = String(raw.label || raw.gateway || "").toLowerCase();
	if (label.includes("mpesa") || label.includes("m-pesa")) return ["mpesa", "link"];
	return ["redirect", "link"];
}

export function normalizeOnlineGateway(raw: any): OnlineGateway {
	return {
		id: raw.id || raw.gateway || "",
		name: raw.label || raw.name || raw.gateway || "",
		label: raw.label || raw.gateway || "",
		gateway: raw.gateway || "",
		providerType: inferGatewayProviderType(raw),
		capabilities: inferGatewayCapabilities(raw),
		details: raw.details || "",
	};
}

// ----- Service functions -----

function parseServiceError(error: any, fallback: string): Error {
	if (error instanceof Error) return error;
	const msg =
		error?.message ||
		(Array.isArray(error?.messages) ? error.messages.join(" ") : null) ||
		fallback;
	return new Error(msg);
}

export async function fetchCheckoutSummary(bookingId: string): Promise<CheckoutSummary> {
	try {
		const payload = await getCheckoutSummaryApi(bookingId);
		return normalizeCheckoutSummary(payload);
	} catch (error) {
		throw parseServiceError(error, "Checkout summary could not be loaded.");
	}
}

export async function fetchOnlineGateways(bookingId: string): Promise<{
	gateways: OnlineGateway[];
	defaultGatewayId: string;
}> {
	try {
		const payload = await getOnlineGatewaysApi(bookingId);
		const gateways = Array.isArray(payload?.methods)
			? payload.methods.map(normalizeOnlineGateway)
			: [];
		const defaultGatewayId = payload?.defaultMethodId || gateways[0]?.id || "";
		return { gateways, defaultGatewayId };
	} catch (error) {
		throw parseServiceError(error, "Payment gateways could not be loaded.");
	}
}

export async function initiateOnlinePayment(params: {
	bookingId: string;
	gateway: string;
	redirectTo?: string;
	phoneNumber?: string;
	amount?: number;
	paymentType?: "full" | "deposit";
}): Promise<PaymentLinkResult> {
	try {
		const payload = await createPaymentLinkApi({
			bookingId: params.bookingId,
			paymentGateway: params.gateway,
			redirectTo: params.redirectTo,
			phoneNumber: params.phoneNumber,
			amount: params.amount,
			paymentType: params.paymentType,
		});
		const paymentUrl = payload?.payment_url || payload?.url || payload?.redirect_url || "";

		return {
			paymentUrl,
			url: payload?.url || payload?.redirect_url || "",
			redirectUrl: payload?.redirect_url || payload?.url || "",
			status: payload?.status || "",
			message: payload?.message || "",
			checkout: payload?.checkout ? normalizeCheckoutSummary(payload.checkout) : undefined,
			raw: payload,
		};
	} catch (error) {
		throw parseServiceError(error, "Payment could not be initiated.");
	}
}
