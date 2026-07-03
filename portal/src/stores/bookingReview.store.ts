import { defineStore } from "pinia";
import {
	getBookingPricingSummaryApi,
	applyBookingCouponApi,
	removeBookingCouponApi,
	applyAppointmentCouponApi,
	removeAppointmentCouponApi,
} from "@/api/bookingReview.api";
import type { AppointmentPricingBreakdown } from "@/services/checkout.service";

export interface ReviewBookingInfo {
	name: string;
	customer: string;
	fullName: string;
	email: string;
	mobileNo: string;
	status: string;
	currency: string;
	totalGuests: number;
	appointmentCount: number;
}

export interface ReviewPricingSummary {
	subtotal: number;
	appointmentDiscountTotal: number;
	bookingDiscountAmount: number;
	intermediateTotal: number;
	finalAmount: number;
	currency: string;
}

export type CouponStrategy = "booking" | "appointment" | "none";

const createEmptyBookingInfo = (): ReviewBookingInfo => ({
	name: "",
	customer: "",
	fullName: "",
	email: "",
	mobileNo: "",
	status: "Draft",
	currency: "KES",
	totalGuests: 0,
	appointmentCount: 0,
});

const createEmptyPricingSummary = (): ReviewPricingSummary => ({
	subtotal: 0,
	appointmentDiscountTotal: 0,
	bookingDiscountAmount: 0,
	intermediateTotal: 0,
	finalAmount: 0,
	currency: "KES",
});

function normalizeBreakdown(items: any[], currency: string): AppointmentPricingBreakdown[] {
	return items.map((item: any) => ({
		appointmentId: item?.appointmentId || item?.name || "",
		serviceType: item?.serviceType || item?.appointmentType || "",
		guestName: item?.guestName || item?.fullName || "",
		date: item?.date || item?.appointmentDate || "",
		startTime: item?.startTime || item?.start_time || "",
		endTime: item?.endTime || item?.end_time || "",
		provider: item?.provider || "",
		status: item?.status || "",
		paymentStatus: item?.paymentStatus || "",
		currency: item?.currency || currency,
		baseAmount: Number(item?.baseAmount || item?.totalAmount || 0),
		appointmentDiscountAmount: Number(item?.appointmentDiscountAmount || item?.discountAmount || 0),
		finalAmount: Number(item?.finalAmount || item?.grandTotal || item?.totalAmount || 0),
		outstandingAmount: Number(item?.outstandingAmount || 0),
		appointmentCouponCode: item?.appointmentCouponCode || item?.couponCode || "",
	}));
}

function normalizePricingSummaryResponse(raw: any, bookingId: string) {
	const currency = raw?.currency || "KES";
	const couponRaw = raw?.coupon || {};
	const breakdown = normalizeBreakdown(
		Array.isArray(raw?.appointmentBreakdown) ? raw.appointmentBreakdown : [],
		currency,
	);
	return {
		bookingInfo: {
			name: raw?.bookingId || bookingId,
			customer: "",
			fullName: "",
			email: "",
			mobileNo: "",
			status: "Draft",
			currency,
			totalGuests: breakdown.length,
			appointmentCount: breakdown.length,
		} as ReviewBookingInfo,
		pricingSummary: {
			subtotal: Number(raw?.subtotal || 0),
			appointmentDiscountTotal: Number(raw?.appointmentDiscountTotal || 0),
			bookingDiscountAmount: Number(raw?.bookingDiscountAmount || 0),
			intermediateTotal: Number(raw?.intermediateTotal || 0),
			finalAmount: Number(raw?.finalAmount || 0),
			currency,
		} as ReviewPricingSummary,
		bookingCouponCode: couponRaw?.code || "",
		appointmentBreakdown: breakdown,
	};
}

function normalizeCouponApplyResponse(raw: any) {
	const checkout = raw?.checkout;
	if (!checkout) return null;
	const pricing = checkout?.pricing || {};
	const booking = checkout?.booking || {};
	const currency = booking?.currency || checkout?.payment?.currency || "KES";
	return {
		pricingSummary: {
			subtotal: Number(pricing?.subtotalAmount || 0),
			appointmentDiscountTotal: Number(pricing?.appointmentDiscountTotal || 0),
			bookingDiscountAmount: Number(pricing?.bookingDiscountAmount || 0),
			intermediateTotal: Number(pricing?.intermediateTotal || 0),
			finalAmount: Number(pricing?.finalAmount || 0),
			currency,
		} as ReviewPricingSummary,
		appointmentBreakdown: normalizeBreakdown(
			Array.isArray(pricing?.appointmentBreakdown) ? pricing.appointmentBreakdown : [],
			currency,
		),
		bookingCouponCode:
			pricing?.bookingCoupon?.code ||
			pricing?.bookingCoupon?.name ||
			booking?.couponCode ||
			"",
	};
}

export const useBookingReviewStore = defineStore("booking-review", {
	state: () => ({
		bookingId: "",
		bookingInfo: createEmptyBookingInfo() as ReviewBookingInfo,
		pricingSummary: createEmptyPricingSummary() as ReviewPricingSummary,
		appointmentBreakdown: [] as AppointmentPricingBreakdown[],

		bookingCouponCode: "",
		bookingCouponDraft: "",
		bookingCouponError: "",
		bookingCouponSuccess: "",
		isApplyingBookingCoupon: false,
		isRemovingBookingCoupon: false,

		appointmentCouponDrafts: {} as Record<string, string>,
		appointmentCouponErrors: {} as Record<string, string>,
		appointmentCouponBusy: {} as Record<string, boolean>,

		pendingStrategySwitch: null as null | {
			type: "booking" | "appointment";
			appointmentId?: string;
		},

		isLoading: false,
		error: "",
	}),

	getters: {
		currency(state): string {
			return state.pricingSummary.currency || state.bookingInfo.currency || "KES";
		},
		couponStrategy(state): CouponStrategy {
			if (state.bookingCouponCode) return "booking";
			if (state.appointmentBreakdown.some((a) => Boolean(a.appointmentCouponCode)))
				return "appointment";
			return "none";
		},
		isBookingCouponLocked(state): boolean {
			return state.appointmentBreakdown.some((a) => Boolean(a.appointmentCouponCode));
		},
		areAppointmentCouponsLocked(state): boolean {
			return Boolean(state.bookingCouponCode);
		},
		canProceedToCheckout(state): boolean {
			return (
				!state.isLoading &&
				Boolean(state.bookingId) &&
				!state.isApplyingBookingCoupon &&
				!state.isRemovingBookingCoupon &&
				!Object.values(state.appointmentCouponBusy).some(Boolean)
			);
		},
		totalDiscount(state): number {
			return (
				Number(state.pricingSummary.appointmentDiscountTotal || 0) +
				Number(state.pricingSummary.bookingDiscountAmount || 0)
			);
		},
	},

	actions: {
		_syncFromNormalized(n: {
			pricingSummary: ReviewPricingSummary;
			appointmentBreakdown: AppointmentPricingBreakdown[];
			bookingCouponCode: string;
		}) {
			this.pricingSummary = n.pricingSummary;
			this.appointmentBreakdown = n.appointmentBreakdown;
			this.bookingCouponCode = n.bookingCouponCode;
		},

		async fetchPricingSummary(bookingId: string) {
			if (!bookingId) return;
			this.bookingId = bookingId;
			this.isLoading = true;
			this.error = "";
			try {
				const raw = await getBookingPricingSummaryApi(bookingId);
				if (!raw) { this.error = "Could not load pricing summary."; return; }
				const n = normalizePricingSummaryResponse(raw, bookingId);
				this.bookingInfo = n.bookingInfo;
				this._syncFromNormalized(n);
			} catch (err: any) {
				this.error = err?.message || "Failed to load booking pricing.";
			} finally {
				this.isLoading = false;
			}
		},

		setBookingCouponDraft(value: string) {
			this.bookingCouponDraft = value;
			this.bookingCouponError = "";
		},

		async applyBookingCoupon() {
			const code = (this.bookingCouponDraft || "").trim();
			if (!code || !this.bookingId) return;
			if (this.isBookingCouponLocked) {
				this.pendingStrategySwitch = { type: "booking" };
				return;
			}
			await this._doApplyBookingCoupon(code);
		},

		async _doApplyBookingCoupon(code: string) {
			this.isApplyingBookingCoupon = true;
			this.bookingCouponError = "";
			this.bookingCouponSuccess = "";
			try {
				const raw = await applyBookingCouponApi(this.bookingId, code);
				if (!raw) { this.bookingCouponError = "Failed to apply coupon."; return; }
				const n = normalizeCouponApplyResponse(raw);
				if (n) {
					this._syncFromNormalized(n);
				} else {
					await this.fetchPricingSummary(this.bookingId);
				}
				this.bookingCouponSuccess = raw?.message || "Coupon applied.";
				this.bookingCouponDraft = "";
			} catch (err: any) {
				this.bookingCouponError = this._extractError(err, "Failed to apply coupon.");
			} finally {
				this.isApplyingBookingCoupon = false;
			}
		},

		async removeBookingCoupon() {
			if (!this.bookingId || !this.bookingCouponCode) return;
			this.isRemovingBookingCoupon = true;
			this.bookingCouponError = "";
			this.bookingCouponSuccess = "";
			try {
				const raw = await removeBookingCouponApi(this.bookingId);
				if (!raw) return;
				const n = normalizeCouponApplyResponse(raw);
				if (n) {
					this._syncFromNormalized(n);
				} else {
					await this.fetchPricingSummary(this.bookingId);
				}
				this.bookingCouponCode = "";
				this.bookingCouponDraft = "";
			} catch (err: any) {
				this.bookingCouponError = this._extractError(err, "Failed to remove coupon.");
			} finally {
				this.isRemovingBookingCoupon = false;
			}
		},

		setAppointmentCouponDraft(appointmentId: string, value: string) {
			this.appointmentCouponDrafts = { ...this.appointmentCouponDrafts, [appointmentId]: value };
			this.appointmentCouponErrors = { ...this.appointmentCouponErrors, [appointmentId]: "" };
		},

		async applyAppointmentCoupon(appointmentId: string) {
			const code = (this.appointmentCouponDrafts[appointmentId] || "").trim();
			if (!code || !this.bookingId || !appointmentId) return;
			if (this.areAppointmentCouponsLocked) {
				this.pendingStrategySwitch = { type: "appointment", appointmentId };
				return;
			}
			await this._doApplyAppointmentCoupon(appointmentId, code);
		},

		async _doApplyAppointmentCoupon(appointmentId: string, code: string) {
			this.appointmentCouponBusy = { ...this.appointmentCouponBusy, [appointmentId]: true };
			this.appointmentCouponErrors = { ...this.appointmentCouponErrors, [appointmentId]: "" };
			try {
				const raw = await applyAppointmentCouponApi(this.bookingId, appointmentId, code);
				if (!raw) {
					this.appointmentCouponErrors = { ...this.appointmentCouponErrors, [appointmentId]: "Failed to apply coupon." };
					return;
				}
				const n = normalizeCouponApplyResponse(raw);
				if (n) {
					this._syncFromNormalized(n);
				} else {
					await this.fetchPricingSummary(this.bookingId);
				}
				this.appointmentCouponDrafts = { ...this.appointmentCouponDrafts, [appointmentId]: "" };
			} catch (err: any) {
				this.appointmentCouponErrors = {
					...this.appointmentCouponErrors,
					[appointmentId]: this._extractError(err, "Failed to apply coupon."),
				};
			} finally {
				this.appointmentCouponBusy = { ...this.appointmentCouponBusy, [appointmentId]: false };
			}
		},

		async removeAppointmentCoupon(appointmentId: string) {
			if (!this.bookingId || !appointmentId) return;
			this.appointmentCouponBusy = { ...this.appointmentCouponBusy, [appointmentId]: true };
			this.appointmentCouponErrors = { ...this.appointmentCouponErrors, [appointmentId]: "" };
			try {
				const raw = await removeAppointmentCouponApi(this.bookingId, appointmentId);
				if (!raw) return;
				const n = normalizeCouponApplyResponse(raw);
				if (n) {
					this._syncFromNormalized(n);
				} else {
					await this.fetchPricingSummary(this.bookingId);
				}
			} catch (err: any) {
				this.appointmentCouponErrors = {
					...this.appointmentCouponErrors,
					[appointmentId]: this._extractError(err, "Failed to remove coupon."),
				};
			} finally {
				this.appointmentCouponBusy = { ...this.appointmentCouponBusy, [appointmentId]: false };
			}
		},

		async confirmStrategySwitch() {
			const pending = this.pendingStrategySwitch;
			if (!pending) return;
			this.pendingStrategySwitch = null;
			if (pending.type === "booking") {
				const ids = this.appointmentBreakdown
					.filter((a) => Boolean(a.appointmentCouponCode))
					.map((a) => a.appointmentId);
				for (const id of ids) await this.removeAppointmentCoupon(id);
				const code = (this.bookingCouponDraft || "").trim();
				if (code) await this._doApplyBookingCoupon(code);
			} else if (pending.type === "appointment" && pending.appointmentId) {
				await this.removeBookingCoupon();
				const code = (this.appointmentCouponDrafts[pending.appointmentId] || "").trim();
				if (code) await this._doApplyAppointmentCoupon(pending.appointmentId, code);
			}
		},

		cancelStrategySwitch() {
			this.pendingStrategySwitch = null;
		},

		_extractError(err: any, fallback: string): string {
			return err?.message || fallback;
		},

		reset() {
			this.$reset();
		},
	},
});
