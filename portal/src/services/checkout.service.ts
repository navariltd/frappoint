import {
	getCheckoutSummaryApi,
	getOnlineGatewaysApi,
	createPaymentLinkApi,
	validateCheckoutCouponApi,
	applyCheckoutCouponApi,
	removeCheckoutCouponApi,
} from "@/api/checkout.api";
import { getErrorMessage } from "@/utils/errorMessage";

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
	grandTotal: number;
	discountAmount: number;
	couponCode: string;
	currency: string;
}

export interface AppointmentPricingBreakdown {
	appointmentId: string;
	serviceType: string;
	guestName: string;
	date: string;
	startTime: string;
	endTime: string;
	provider: string;
	status: string;
	paymentStatus: string;
	currency: string;
	baseAmount: number;
	appointmentDiscountAmount: number;
	finalAmount: number;
	outstandingAmount: number;
	appointmentCouponCode: string;
}

export interface CouponAppointmentBreakdown {
	appointmentId: string;
	serviceType: string;
	guestName: string;
	totalAmount: number;
	grandTotal: number;
	discountAmount: number;
}

export interface AppliedCoupon {
	coupon: string;
	discountAmount: number;
	appointments: CouponAppointmentBreakdown[];
}

export interface CheckoutCouponSummary {
	hasCoupon: boolean;
	totalDiscount: number;
	appliedCoupons: AppliedCoupon[];
}

export interface CheckoutCouponMeta {
	name: string;
	code: string;
	couponType: string;
	discountType: string;
	discountValue: number;
	maximumDiscountAmount: number;
	minimumOrderValue: number;
	scope: string;
}

export interface CouponEvaluationItem {
	appointmentId: string;
	serviceType: string;
	guestName: string;
	totalAmount?: number;
	discountAmount?: number;
	reason?: string;
}

export interface CheckoutCouponValidation {
	valid: boolean;
	message: string;
	coupon: CheckoutCouponMeta | null;
	evaluation: {
		eligible: CouponEvaluationItem[];
		ineligible: CouponEvaluationItem[];
		previewDiscount: number;
		scope: string;
	};
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

export interface BookingPricingSummary {
	subtotalAmount: number;
	appointmentDiscountTotal: number;
	bookingDiscountAmount: number;
	totalAmount: number;
	finalAmount: number;
	intermediateTotal: number;
	appointmentBreakdown: AppointmentPricingBreakdown[];
	bookingCoupon: CheckoutCouponMeta | null;
	appointmentCoupons: AppliedCoupon[];
}

export interface CheckoutSummary {
	booking: CheckoutBookingSummary;
	payment: CheckoutPaymentSummary;
	coupon: CheckoutCouponSummary;
	pricing: BookingPricingSummary;
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
		coupon: {
			hasCoupon: false,
			totalDiscount: 0,
			appliedCoupons: [],
		},
		pricing: {
			subtotalAmount: 0,
			appointmentDiscountTotal: 0,
			bookingDiscountAmount: 0,
			totalAmount: 0,
			finalAmount: 0,
			intermediateTotal: 0,
			appointmentBreakdown: [],
			bookingCoupon: null,
			appointmentCoupons: [],
		},
	};
}

// ----- Normalizers (ported from booking_desk services) -----

function normalizeAppointment(raw: any): CheckoutAppointment {
	return {
		name: raw?.name || "",
		appointmentType: raw?.appointment_type || raw?.appointmentType || raw?.serviceType || "",
		guestName: raw?.guest_full_name || raw?.guestName || raw?.full_name || raw?.fullName || "",
		date: raw?.appointment_date || raw?.date || "",
		startTime: raw?.start_time || raw?.startTime || "",
		endTime: raw?.end_time || raw?.endTime || "",
		status: raw?.status || "",
		price: Number(raw?.price || raw?.rate || raw?.total_amount || raw?.totalAmount || 0),
		grandTotal: Number(
			raw?.grand_total || raw?.grandTotal || raw?.price || raw?.rate || raw?.total_amount || raw?.totalAmount || 0
		),
		discountAmount: Number(raw?.discount_amount || raw?.discountAmount || 0),
		couponCode: raw?.coupon_code || raw?.couponCode || "",
		currency: raw?.currency || "",
	};
}

function normalizeCouponSummary(raw: any): CheckoutCouponSummary {
	const appliedCoupons = Array.isArray(raw?.appliedCoupons)
		? raw.appliedCoupons.map((row: any) => ({
				coupon: row?.coupon || "",
				discountAmount: Number(row?.discountAmount || 0),
				appointments: Array.isArray(row?.appointments)
					? row.appointments.map((appt: any) => ({
							appointmentId: appt?.appointmentId || "",
							serviceType: appt?.serviceType || "",
							guestName: appt?.guestName || "",
							totalAmount: Number(appt?.totalAmount || 0),
							grandTotal: Number(appt?.grandTotal || appt?.totalAmount || 0),
							discountAmount: Number(appt?.discountAmount || 0),
						}))
					: [],
		  }))
		: [];

	return {
		hasCoupon: Boolean(raw?.hasCoupon || appliedCoupons.length),
		totalDiscount: Number(raw?.totalDiscount || 0),
		appliedCoupons,
	};
}

function normalizeCouponValidation(payload: any): CheckoutCouponValidation {
	const evaluation = payload?.evaluation || {};
	return {
		valid: Boolean(payload?.valid),
		message: payload?.message || "",
		coupon: payload?.coupon
			? {
					name: payload.coupon.name || "",
					code: payload.coupon.code || "",
					couponType: payload.coupon.couponType || "",
					discountType: payload.coupon.discountType || "",
					discountValue: Number(payload.coupon.discountValue || 0),
					maximumDiscountAmount: Number(payload.coupon.maximumDiscountAmount || 0),
					minimumOrderValue: Number(payload.coupon.minimumOrderValue || 0),
					scope: payload.coupon.scope || evaluation?.scope || "",
			  }
			: null,
		evaluation: {
			eligible: Array.isArray(evaluation?.eligible)
				? evaluation.eligible.map((row: any) => ({
						appointmentId: row?.appointmentId || "",
						serviceType: row?.serviceType || "",
						guestName: row?.guestName || "",
						totalAmount: Number(row?.totalAmount || 0),
						discountAmount: Number(row?.discountAmount || 0),
				  }))
				: [],
			ineligible: Array.isArray(evaluation?.ineligible)
				? evaluation.ineligible.map((row: any) => ({
						appointmentId: row?.appointmentId || "",
						serviceType: row?.serviceType || "",
						guestName: row?.guestName || "",
						reason: row?.reason || "",
				  }))
				: [],
			previewDiscount: Number(evaluation?.previewDiscount || 0),
			scope: evaluation?.scope || "",
		},
	};
}

function normalizeCouponMeta(raw: any): CheckoutCouponMeta | null {
	if (!raw) return null;
	return {
		name: raw?.name || "",
		code: raw?.code || "",
		couponType: raw?.couponType || raw?.coupon_type || "",
		discountType: raw?.discountType || raw?.discount_type || "",
		discountValue: Number(raw?.discountValue || raw?.discount_value || 0),
		maximumDiscountAmount: Number(raw?.maximumDiscountAmount || raw?.maximum_discount_amount || 0),
		minimumOrderValue: Number(raw?.minimumOrderValue || raw?.minimum_order_value || 0),
		scope: raw?.scope || "",
	};
}

function normalizeAppliedCoupon(raw: any): AppliedCoupon {
	return {
		coupon: raw?.coupon || raw?.code || raw?.name || "",
		discountAmount: Number(raw?.discountAmount || raw?.discount_amount || 0),
		appointments: Array.isArray(raw?.appointments)
			? raw.appointments.map((appt: any) => ({
					appointmentId: appt?.appointmentId || "",
					serviceType: appt?.serviceType || "",
					guestName: appt?.guestName || "",
					totalAmount: Number(appt?.totalAmount || 0),
					grandTotal: Number(appt?.grandTotal || appt?.totalAmount || 0),
					discountAmount: Number(appt?.discountAmount || 0),
			  }))
			: [],
	};
}

function normalizeAppointmentPricing(raw: any): AppointmentPricingBreakdown {
	return {
		appointmentId: raw?.appointmentId || raw?.name || "",
		serviceType: raw?.serviceType || raw?.appointmentType || "",
		guestName: raw?.guestName || raw?.fullName || "",
		date: raw?.date || "",
		startTime: raw?.startTime || "",
		endTime: raw?.endTime || "",
		provider: raw?.provider || "",
		status: raw?.status || "",
		paymentStatus: raw?.paymentStatus || "",
		currency: raw?.currency || "KES",
		baseAmount: Number(raw?.baseAmount || raw?.totalAmount || 0),
		appointmentDiscountAmount: Number(raw?.appointmentDiscountAmount || raw?.discountAmount || 0),
		finalAmount: Number(raw?.finalAmount || raw?.grandTotal || 0),
		outstandingAmount: Number(raw?.outstandingAmount || 0),
		appointmentCouponCode: raw?.appointmentCouponCode || raw?.couponCode || "",
	};
}

function normalizePricingSummary(raw: any): BookingPricingSummary {
	const appointmentCoupons = Array.isArray(raw?.appointmentCoupons)
		? raw.appointmentCoupons.map(normalizeAppliedCoupon)
		: [];

	return {
		subtotalAmount: Number(raw?.subtotalAmount || raw?.subtotal_amount || 0),
		appointmentDiscountTotal: Number(
			raw?.appointmentDiscountTotal || raw?.appointment_discount_total || 0
		),
		bookingDiscountAmount: Number(raw?.bookingDiscountAmount || raw?.booking_discount_amount || 0),
		totalAmount: Number(raw?.totalAmount || raw?.total_amount || 0),
		finalAmount: Number(raw?.finalAmount || raw?.final_amount || 0),
		intermediateTotal: Number(raw?.intermediateTotal || raw?.intermediate_total || 0),
		appointmentBreakdown: Array.isArray(raw?.appointmentBreakdown)
			? raw.appointmentBreakdown.map(normalizeAppointmentPricing)
			: [],
		bookingCoupon: normalizeCouponMeta(raw?.bookingCoupon),
		appointmentCoupons,
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
	const pricingRaw = payload.pricing || bookingRaw.pricing || {};

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
		coupon: normalizeCouponSummary(payload.coupon || {}),
		pricing: normalizePricingSummary(pricingRaw),
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
	return new Error(getErrorMessage(error, fallback));
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
	couponCode?: string;
	finalAmountReference?: number;
}): Promise<PaymentLinkResult> {
	try {
		const payload = await createPaymentLinkApi({
			bookingId: params.bookingId,
			paymentGateway: params.gateway,
			redirectTo: params.redirectTo,
			phoneNumber: params.phoneNumber,
			amount: params.amount,
			paymentType: params.paymentType,
			couponCode: params.couponCode,
			finalAmountReference: params.finalAmountReference,
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

export async function validateCheckoutCoupon(
	bookingId: string,
	couponCode: string
): Promise<CheckoutCouponValidation> {
	try {
		const payload = await validateCheckoutCouponApi(bookingId, couponCode);
		return normalizeCouponValidation(payload);
	} catch (error) {
		throw parseServiceError(error, "Coupon could not be validated.");
	}
}

export async function applyCheckoutCoupon(
	bookingId: string,
	couponCode: string
): Promise<{ message: string; checkout: CheckoutSummary; evaluation: CheckoutCouponValidation["evaluation"] }> {
	try {
		const payload = await applyCheckoutCouponApi(bookingId, couponCode);
		return {
			message: payload?.message || "Coupon applied.",
			checkout: normalizeCheckoutSummary(payload?.checkout),
			evaluation: normalizeCouponValidation({ evaluation: payload?.evaluation }).evaluation,
		};
	} catch (error) {
		throw parseServiceError(error, "Coupon could not be applied.");
	}
}

export async function removeCheckoutCoupon(
	bookingId: string,
	couponCode?: string
): Promise<{ message: string; checkout: CheckoutSummary }> {
	try {
		const payload = await removeCheckoutCouponApi(bookingId, couponCode);
		return {
			message: payload?.message || "Coupon removed.",
			checkout: normalizeCheckoutSummary(payload?.checkout),
		};
	} catch (error) {
		throw parseServiceError(error, "Coupon could not be removed.");
	}
}
