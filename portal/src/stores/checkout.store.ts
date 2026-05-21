import { defineStore } from "pinia";
import {
	fetchCheckoutSummary,
	fetchOnlineGateways,
	initiateOnlinePayment,
	createEmptyCheckoutSummary,
	validateCheckoutCoupon,
	applyCheckoutCoupon,
	removeCheckoutCoupon,
	type AppliedCoupon,
	type AppointmentPricingBreakdown,
	type BookingPricingSummary,
	type CheckoutSummary,
	type CheckoutCouponMeta,
	type OnlineGateway,
	type CheckoutCouponValidation,
} from "@/services/checkout.service";

export type PaymentType = "full" | "deposit";
export type PaymentProgress = "idle" | "processing" | "redirecting" | "failed";

const STORAGE_KEY = "frappoint-checkout-session";
const DEPOSIT_FALLBACK_PERCENT = 30;
const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

export interface PersistedCheckoutSession {
	bookingId: string;
	selectedPaymentType: PaymentType;
	selectedGatewayId: string;
	mpesaPhone: string;
	couponCode: string;
}

export const useCheckoutStore = defineStore("checkout", {
	state: () => ({
		bookingId: "",
		summary: createEmptyCheckoutSummary() as CheckoutSummary,
		bookingPricingSummary: createEmptyCheckoutSummary().pricing as BookingPricingSummary,
		appointmentPricingBreakdown: [] as AppointmentPricingBreakdown[],
		appliedBookingCoupon: null as CheckoutCouponMeta | null,
		appliedAppointmentCoupons: [] as AppliedCoupon[],
		gateways: [] as OnlineGateway[],
		selectedPaymentType: "full" as PaymentType,
		selectedGatewayId: "",
		depositAmount: 0,
		couponCode: "",
		couponDraft: "",
		couponValidation: null as CheckoutCouponValidation | null,
		couponMessage: "",
		couponError: "",
		isValidatingCoupon: false,
		isApplyingCoupon: false,
		mpesaPhone: "",
		paymentProgress: "idle" as PaymentProgress,
		statusMessage: "",
		hostedPaymentUrl: "",
		paymentSession: null as any,
		paymentOptionSource: "backend" as "backend" | "manual",
		isLoading: false,
		isSubmitting: false,
		error: "",
	}),

	getters: {
		booking(state) {
			return state.summary.booking;
		},
		payment(state) {
			return state.summary.payment;
		},
		selectedGateway(state): OnlineGateway | null {
			return state.gateways.find((g) => g.id === state.selectedGatewayId) || null;
		},
		totalSavings(state): number {
			return Number(
				state.bookingPricingSummary.appointmentDiscountTotal
					+ state.bookingPricingSummary.bookingDiscountAmount
			);
		},
		discountedTotal(state): number {
			return Number(state.bookingPricingSummary.finalAmount || 0);
		},
		appliedCoupon(state) {
			return state.appliedBookingCoupon || state.appliedAppointmentCoupons[0] || null;
		},
		payableAmount(state): number {
			const outstanding = Number(state.summary.payment.outstandingAmount || 0);
			if (state.selectedPaymentType === "full") return outstanding;

			const minimumDue = Number(state.summary.payment.minimumDue || 0);
			const safeDeposit = clamp(
				Number(state.depositAmount || minimumDue),
				minimumDue,
				outstanding
			);
			return safeDeposit;
		},
		remainingAfterPayment(state): number {
			const outstanding = Number(state.summary.payment.outstandingAmount || 0);
			const payable = (this as any).payableAmount;
			return Math.max(0, outstanding - payable);
		},
		isBookingPaid(state): boolean {
			return Number(state.summary.payment.outstandingAmount || 0) <= 0;
		},
		isMpesaGateway(state): boolean {
			const gw = state.gateways.find((g) => g.id === state.selectedGatewayId);
			return gw?.providerType === "mpesa";
		},
		depositPercent(state): number {
			return Number(state.summary.payment.depositPercent || DEPOSIT_FALLBACK_PERCENT);
		},
		calculatedDepositAmount(state): number {
			const total = Number(state.summary.payment.outstandingAmount || 0);
			const percent = Number(state.summary.payment.depositPercent || DEPOSIT_FALLBACK_PERCENT);
			return Math.ceil((total * percent) / 100);
		},
		canSubmit(state): boolean {
			if (state.isSubmitting || state.isLoading) return false;
			if (state.isApplyingCoupon || state.isValidatingCoupon) return false;
			if (!state.bookingId) return false;
			if (!state.selectedGatewayId) return false;
			if ((this as any).payableAmount <= 0) return false;
			if ((this as any).isMpesaGateway && !state.mpesaPhone) return false;
			return true;
		},
		currency(state): string {
			return state.summary.payment.currency || state.summary.booking.currency || "KES";
		},
	},

	actions: {
		syncPricingState(summary: CheckoutSummary) {
			this.summary = summary;
			this.bookingPricingSummary = summary.pricing;
			this.appointmentPricingBreakdown = summary.pricing.appointmentBreakdown || [];
			this.appliedBookingCoupon = summary.pricing.bookingCoupon;
			this.appliedAppointmentCoupons = summary.pricing.appointmentCoupons || [];
		},

		persistSession() {
			if (typeof window === "undefined") return;
			const session: PersistedCheckoutSession = {
				bookingId: this.bookingId,
				selectedPaymentType: this.selectedPaymentType,
				selectedGatewayId: this.selectedGatewayId,
				mpesaPhone: this.mpesaPhone,
				couponCode: this.couponCode,
			};
			window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
		},

		restoreSession(): PersistedCheckoutSession | null {
			if (typeof window === "undefined") return null;
			try {
				const raw = window.localStorage.getItem(STORAGE_KEY);
				if (!raw) return null;
				return JSON.parse(raw) as PersistedCheckoutSession;
			} catch {
				return null;
			}
		},

		clearSession() {
			if (typeof window !== "undefined") {
				window.localStorage.removeItem(STORAGE_KEY);
			}
		},

		clearCheckout() {
			this.bookingId = "";
			this.summary = createEmptyCheckoutSummary();
			this.bookingPricingSummary = createEmptyCheckoutSummary().pricing;
			this.appointmentPricingBreakdown = [];
			this.appliedBookingCoupon = null;
			this.appliedAppointmentCoupons = [];
			this.gateways = [];
			this.selectedPaymentType = "full";
			this.selectedGatewayId = "";
			this.depositAmount = 0;
			this.couponCode = "";
			this.couponDraft = "";
			this.couponValidation = null;
			this.couponMessage = "";
			this.couponError = "";
			this.isValidatingCoupon = false;
			this.isApplyingCoupon = false;
			this.mpesaPhone = "";
			this.paymentProgress = "idle";
			this.statusMessage = "";
			this.hostedPaymentUrl = "";
			this.paymentSession = null;
			this.isLoading = false;
			this.isSubmitting = false;
			this.error = "";
			this.clearSession();
		},

		setPaymentType(type: PaymentType) {
			this.selectedPaymentType = type;
			this.paymentOptionSource = "manual";
			if (type === "full") {
				this.depositAmount = 0;
			} else {
				const minimumDue = Number(this.summary.payment.minimumDue || 0);
				const calculated = (this as any).calculatedDepositAmount;
				this.depositAmount = calculated > 0 ? calculated : minimumDue;
			}

			this.persistSession();
		},

		setGateway(gatewayId: string) {
			this.selectedGatewayId = gatewayId;
			this.hostedPaymentUrl = "";
			this.paymentSession = null;
			this.statusMessage = "";
			this.paymentProgress = "idle";
			this.persistSession();
		},

		selectGateway(gatewayId: string) {
			this.setGateway(gatewayId);
		},

		selectPaymentOption(type: PaymentType) {
			this.setPaymentType(type);
		},

		setMpesaPhone(phone: string) {
			this.mpesaPhone = phone;
			this.persistSession();
		},

		setDepositAmount(amount: number) {
			this.depositAmount = Number(amount || 0);
		},

		setCouponDraft(code: string) {
			this.couponDraft = String(code || "").trim().toUpperCase();
			this.couponError = "";
			this.couponMessage = "";
		},

		async validateCoupon(code?: string) {
			if (!this.bookingId) return null;
			const value = String(code ?? this.couponDraft ?? "").trim().toUpperCase();
			if (!value) {
				this.couponError = "Enter a coupon code to continue.";
				this.couponValidation = null;
				return null;
			}

			this.isValidatingCoupon = true;
			this.couponError = "";
			this.couponMessage = "";
			try {
				const validation = await validateCheckoutCoupon(this.bookingId, value);
				this.couponValidation = validation;
				if (!validation.valid) {
					this.couponError = validation.message || "Coupon is not valid for this booking.";
				}
				return validation;
			} catch (error: any) {
				this.couponValidation = null;
				this.couponError = error?.message || "Coupon validation failed.";
				return null;
			} finally {
				this.isValidatingCoupon = false;
			}
		},

		async applyCoupon(code?: string) {
			if (!this.bookingId) return;
			const value = String(code ?? this.couponDraft ?? "").trim().toUpperCase();
			if (!value) {
				this.couponError = "Enter a coupon code to continue.";
				return;
			}

			this.isApplyingCoupon = true;
			this.couponError = "";
			this.couponMessage = "";
			try {
				const validation = await this.validateCoupon(value);
				if (!validation?.valid) {
					return;
				}

				const response = await applyCheckoutCoupon(this.bookingId, value);
				this.syncPricingState(response.checkout);
				this.couponCode = value;
				this.couponDraft = value;
				this.couponValidation = validation;
				this.couponMessage = response.message || "Coupon applied successfully.";
				this.depositAmount = (this as any).calculatedDepositAmount;
				this.persistSession();
			} catch (error: any) {
				this.couponError = error?.message || "Coupon could not be applied.";
			} finally {
				this.isApplyingCoupon = false;
			}
		},

		async removeCoupon() {
			if (!this.bookingId) return;
			this.isApplyingCoupon = true;
			this.couponError = "";
			this.couponMessage = "";
			try {
				const response = await removeCheckoutCoupon(this.bookingId, this.couponCode || undefined);
				this.syncPricingState(response.checkout);
				this.couponCode = "";
				this.couponDraft = "";
				this.couponValidation = null;
				this.couponMessage = response.message || "Coupon removed.";
				this.depositAmount = (this as any).calculatedDepositAmount;
				this.persistSession();
			} catch (error: any) {
				this.couponError = error?.message || "Coupon could not be removed.";
			} finally {
				this.isApplyingCoupon = false;
			}
		},

		async recalculateTotals() {
			await this.refreshSummary();
			this.depositAmount = (this as any).calculatedDepositAmount;
		},

		async initializeCheckout(bookingId: string) {
			this.bookingId = bookingId;
			this.error = "";
			this.isLoading = true;
			this.paymentProgress = "idle";
			this.statusMessage = "";
			this.hostedPaymentUrl = "";
			this.paymentSession = null;

			// Restore persisted session preferences if same booking
			const saved = this.restoreSession();
			if (saved?.bookingId === bookingId) {
				this.selectedPaymentType = saved.selectedPaymentType || "full";
				this.mpesaPhone = saved.mpesaPhone || this.mpesaPhone;
				this.couponCode = saved.couponCode || "";
				this.couponDraft = saved.couponCode || "";
			}

			try {
				const [summary, gatewayPayload] = await Promise.all([
					fetchCheckoutSummary(bookingId),
					fetchOnlineGateways(bookingId),
				]);

				this.syncPricingState(summary);
				this.gateways = gatewayPayload.gateways;

				// Pre-select gateway from session or default
				if (saved?.bookingId === bookingId && saved.selectedGatewayId) {
					this.selectedGatewayId = saved.selectedGatewayId;
				} else if (gatewayPayload.defaultGatewayId) {
					this.selectedGatewayId = gatewayPayload.defaultGatewayId;
				}

				// Set deposit amount
				this.depositAmount = (this as any).calculatedDepositAmount;

				// Auto-extract phone from booking if not already set
				if (!this.mpesaPhone && summary.booking.mobileNo) {
					this.mpesaPhone = summary.booking.mobileNo;
				}
			} catch (error: any) {
				this.error = error?.message || "Checkout could not be initialized.";
				console.error("[CheckoutStore] Initialization failed:", error);
			} finally {
				this.isLoading = false;
			}
		},

		async refreshSummary() {
			if (!this.bookingId) return;
			try {
				this.syncPricingState(await fetchCheckoutSummary(this.bookingId));
			} catch (error: any) {
				this.error = error?.message || "Checkout summary could not be refreshed.";
			}
		},

		async fetchPaymentGateways() {
			if (!this.bookingId) return;
			const gatewayPayload = await fetchOnlineGateways(this.bookingId);
			this.gateways = gatewayPayload.gateways;

			if (!this.selectedGatewayId) {
				this.selectedGatewayId = gatewayPayload.defaultGatewayId || gatewayPayload.gateways[0]?.id || "";
			}

			this.persistSession();
		},

		handlePaymentRedirect(url: string) {
			if (!url) {
				throw new Error("Payment URL was not provided by the server.");
			}

			this.hostedPaymentUrl = url;
			this.paymentProgress = "redirecting";
			this.statusMessage = "Redirecting to secure payment gateway...";
			window.location.href = url;
		},

		async initializePayment() {
			if (!(this as any).canSubmit) {
				this.error = "Please complete all required fields before proceeding.";
				return;
			}

			const gateway = (this as any).selectedGateway as OnlineGateway;
			if (!gateway) {
				this.error = "No payment gateway selected.";
				return;
			}

			this.isSubmitting = true;
			this.error = "";
			this.paymentProgress = "processing";
			this.statusMessage = "Initiating payment...";

			try {
				const redirectTo = `${window.location.origin}/portal/booking/${this.bookingId}`;
				const paymentType = this.selectedPaymentType;
				const outstandingAmount = Number(this.summary.payment.outstandingAmount || 0);
				const minimumDue = Number(this.summary.payment.minimumDue || 0);
				const amount =
					paymentType === "full"
						? outstandingAmount
						: clamp(Number(this.depositAmount || minimumDue), minimumDue, outstandingAmount);

				const result = await initiateOnlinePayment({
					bookingId: this.bookingId,
					gateway: gateway.gateway,
					redirectTo,
					phoneNumber: gateway.providerType === "mpesa" ? this.mpesaPhone : undefined,
					amount,
					paymentType,
					couponCode: this.couponCode || undefined,
					finalAmountReference: Number(this.bookingPricingSummary.finalAmount || 0),
				});

				const paymentUrl = result.paymentUrl || result.url || result.redirectUrl || "";
				this.hostedPaymentUrl = paymentUrl;
				this.paymentSession = result;

				if (result.checkout) {
					this.syncPricingState(result.checkout);
				}

				if (!paymentUrl) {
					throw new Error("Payment gateway did not return a payment URL.");
				}

				this.persistSession();
				this.handlePaymentRedirect(paymentUrl);
				return result;
			} catch (error: any) {
				this.paymentProgress = "failed";
				this.error = error?.message || "Payment could not be initiated.";
				this.statusMessage = "";
				console.error("[CheckoutStore] Payment initiation failed:", error);
				throw error;
			} finally {
				this.isSubmitting = false;
			}
		},

		async initiatePayment() {
			return this.initializePayment();
		},
	},
});
