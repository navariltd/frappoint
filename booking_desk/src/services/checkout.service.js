import {
	applyCheckoutCouponApi,
	confirmCheckoutWithoutPaymentApi,
	getCheckoutSummaryApi,
	recordManualCheckoutPaymentApi,
	removeCheckoutCouponApi,
	validateCheckoutCouponApi,
} from "@/api/checkout.api";
import { createEmptyCheckoutSummary } from "@/types/checkout";

const parseErrorMessage = (error, fallback) => {
	if (!error) return fallback;

	if (Array.isArray(error?.messages) && error.messages.length) {
		return error.messages.join(" ");
	}

	if (error?._server_messages) {
		try {
			const serverMessages = JSON.parse(error._server_messages);
			if (Array.isArray(serverMessages) && serverMessages.length) {
				const first = JSON.parse(serverMessages[0]);
				if (first?.message) return first.message;
			}
		} catch {
			return String(error._server_messages);
		}
	}

	return error?.message || fallback;
};

export { parseErrorMessage };

function normalizeCouponMeta(raw) {
	if (!raw) return null;
	return {
		name: raw.name || "",
		code: raw.code || raw.coupon || "",
		couponType: raw.couponType || raw.coupon_type || "",
		discountType: raw.discountType || raw.discount_type || "",
		discountValue: Number(raw.discountValue || raw.discount_value || 0),
		maximumDiscountAmount: Number(
			raw.maximumDiscountAmount || raw.maximum_discount_amount || 0
		),
		minimumOrderValue: Number(raw.minimumOrderValue || raw.minimum_order_value || 0),
		scope: raw.scope || "",
		discountAmount: Number(raw.discountAmount || raw.discount_amount || 0),
	};
}

function normalizeAppliedCoupon(raw) {
	return {
		coupon: raw?.coupon || raw?.code || raw?.name || "",
		discountAmount: Number(raw?.discountAmount || raw?.discount_amount || 0),
		scope: raw?.scope || "",
		appointments: Array.isArray(raw?.appointments)
			? raw.appointments.map((appointment) => ({
					appointmentId: appointment?.appointmentId || appointment?.name || "",
					serviceType: appointment?.serviceType || appointment?.appointmentType || "",
					guestName: appointment?.guestName || appointment?.fullName || "",
					totalAmount: Number(appointment?.totalAmount || 0),
					grandTotal: Number(appointment?.grandTotal || appointment?.totalAmount || 0),
					discountAmount: Number(appointment?.discountAmount || 0),
			  }))
			: [],
	};
}

function normalizeCouponSummary(raw = {}) {
	const appliedCoupons = Array.isArray(raw.appliedCoupons)
		? raw.appliedCoupons.map(normalizeAppliedCoupon)
		: [];

	return {
		hasCoupon: Boolean(raw.hasCoupon || appliedCoupons.length),
		totalDiscount: Number(raw.totalDiscount || 0),
		appliedCoupons,
		appliedBookingCoupon: normalizeCouponMeta(raw.appliedBookingCoupon),
		appliedAppointmentCoupons: Array.isArray(raw.appliedAppointmentCoupons)
			? raw.appliedAppointmentCoupons.map(normalizeAppliedCoupon)
			: [],
	};
}

function normalizeAppointmentPricing(raw = {}) {
	return {
		appointmentId: raw.appointmentId || raw.name || "",
		serviceType: raw.serviceType || raw.appointmentType || "",
		guestName: raw.guestName || raw.fullName || "",
		date: raw.date || "",
		startTime: raw.startTime || "",
		endTime: raw.endTime || "",
		provider: raw.provider || "",
		status: raw.status || "",
		paymentStatus: raw.paymentStatus || "",
		currency: raw.currency || "KES",
		baseAmount: Number(raw.baseAmount || raw.totalAmount || 0),
		appointmentDiscountAmount: Number(
			raw.appointmentDiscountAmount || raw.discountAmount || 0
		),
		finalAmount: Number(raw.finalAmount || raw.grandTotal || 0),
		outstandingAmount: Number(raw.outstandingAmount || 0),
		appointmentCouponCode: raw.appointmentCouponCode || raw.couponCode || "",
	};
}

function normalizePricingSummary(raw = {}) {
	return {
		subtotalAmount: Number(raw.subtotalAmount || raw.subtotal_amount || 0),
		appointmentDiscountTotal: Number(
			raw.appointmentDiscountTotal || raw.appointment_discount_total || 0
		),
		bookingDiscountAmount: Number(
			raw.bookingDiscountAmount || raw.booking_discount_amount || 0
		),
		totalAmount: Number(raw.totalAmount || raw.total_amount || 0),
		finalAmount: Number(raw.finalAmount || raw.final_amount || 0),
		intermediateTotal: Number(raw.intermediateTotal || raw.intermediate_total || 0),
		appointmentBreakdown: Array.isArray(raw.appointmentBreakdown)
			? raw.appointmentBreakdown.map(normalizeAppointmentPricing)
			: [],
		bookingCoupon: normalizeCouponMeta(raw.bookingCoupon),
		appointmentCoupons: Array.isArray(raw.appointmentCoupons)
			? raw.appointmentCoupons.map(normalizeAppliedCoupon)
			: [],
	};
}

function normalizeCouponValidation(payload = {}) {
	const evaluation = payload.evaluation || {};
	return {
		valid: Boolean(payload.valid),
		message: payload.message || "",
		coupon: normalizeCouponMeta(payload.coupon),
		evaluation: {
			eligible: Array.isArray(evaluation.eligible)
				? evaluation.eligible.map((row) => ({
						appointmentId: row?.appointmentId || "",
						serviceType: row?.serviceType || "",
						guestName: row?.guestName || "",
						totalAmount: Number(row?.totalAmount || 0),
						discountAmount: Number(row?.discountAmount || 0),
				  }))
				: [],
			ineligible: Array.isArray(evaluation.ineligible)
				? evaluation.ineligible.map((row) => ({
						appointmentId: row?.appointmentId || "",
						serviceType: row?.serviceType || "",
						guestName: row?.guestName || "",
						reason: row?.reason || "",
				  }))
				: [],
			previewDiscount: Number(evaluation.previewDiscount || 0),
			scope: evaluation.scope || "",
		},
	};
}

export function normalizeCheckoutSummary(payload) {
	const empty = createEmptyCheckoutSummary();
	if (!payload) return empty;
	const booking = payload.booking || {};
	const payment = payload.payment || {};
	const pricing = payload.pricing || booking.pricing || {};

	return {
		booking: {
			...empty.booking,
			...booking,
			items: Array.isArray(booking.items) ? booking.items : [],
			appointments: Array.isArray(booking.appointments) ? booking.appointments : [],
		},
		payment: {
			...empty.payment,
			...payment,
		},
		coupon: normalizeCouponSummary(payload.coupon || {}),
		pricing: normalizePricingSummary(pricing),
	};
}

export async function fetchCheckoutSummary(bookingId) {
	try {
		const payload = await getCheckoutSummaryApi(bookingId);
		return normalizeCheckoutSummary(payload);
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Checkout summary could not be loaded."));
	}
}

export async function recordManualCheckoutPayment({
	bookingId,
	amount,
	modeOfPayment,
	referenceNo,
}) {
	try {
		const payload = await recordManualCheckoutPaymentApi({
			bookingId,
			amount,
			modeOfPayment,
			referenceNo,
		});
		return {
			paymentName: payload?.paymentName || "",
			checkout: normalizeCheckoutSummary(payload?.checkout),
		};
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Manual payment could not be recorded."));
	}
}

export async function confirmCheckoutWithoutPayment(bookingId) {
	try {
		const payload = await confirmCheckoutWithoutPaymentApi(bookingId);
		return {
			confirmedAppointments: Array.isArray(payload?.confirmedAppointments)
				? payload.confirmedAppointments
				: [],
			checkout: normalizeCheckoutSummary(payload?.checkout),
		};
	} catch (error) {
		throw new Error(
			parseErrorMessage(error, "Booking could not be confirmed without payment.")
		);
	}
}

export async function validateCheckoutCoupon(bookingId, couponCode) {
	try {
		const payload = await validateCheckoutCouponApi(bookingId, couponCode);
		return normalizeCouponValidation(payload);
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Coupon could not be validated."));
	}
}

export async function applyCheckoutCoupon(bookingId, couponCode) {
	try {
		const payload = await applyCheckoutCouponApi(bookingId, couponCode);
		return {
			message: payload?.message || "Coupon applied successfully.",
			checkout: normalizeCheckoutSummary(payload?.checkout),
			evaluation: normalizeCouponValidation({ evaluation: payload?.evaluation }).evaluation,
		};
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Coupon could not be applied."));
	}
}

export async function removeCheckoutCoupon(bookingId, couponCode) {
	try {
		const payload = await removeCheckoutCouponApi(bookingId, couponCode);
		return {
			message: payload?.message || "Coupon removed.",
			checkout: normalizeCheckoutSummary(payload?.checkout),
		};
	} catch (error) {
		throw new Error(parseErrorMessage(error, "Coupon could not be removed."));
	}
}
