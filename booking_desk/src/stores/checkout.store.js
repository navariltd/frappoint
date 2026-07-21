import { defineStore } from "pinia";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";
import {
	applyCheckoutCoupon,
	confirmCheckoutWithoutPayment,
	fetchCheckoutSummary,
	recordManualCheckoutPayment,
	removeCheckoutCoupon,
	validateCheckoutCoupon,
} from "@/services/checkout.service";
import { createHostedCheckoutPayment } from "@/services/payment.service";
import {
	fetchOfflinePaymentMethods,
	fetchOnlinePaymentGateways,
} from "@/services/paymentMethod.service";
import { createEmptyCheckoutSummary } from "@/types/checkout";
import { PAYMENT_CHANNELS, PAYMENT_PROGRESS, PAYMENT_TYPES } from "@/types/payment";
import { CACHE_TAGS, invalidateMemoryCacheByTag } from "@/utils/cachePolicy";

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export const useCheckoutStore = defineStore("checkout", {
	state: () => ({
		bookingId: "",
		summary: createEmptyCheckoutSummary(),
		couponDraft: "",
		couponValidation: null,
		couponMessage: "",
		couponError: "",
		isValidatingCoupon: false,
		isApplyingCoupon: false,
		selectedPaymentChannel: "",
		offlineMethods: [],
		onlineMethods: [],
		selectedPaymentType: PAYMENT_TYPES.FULL,
		selectedMethodId: "",
		paymentModeType: "",
		paymentGatewaySession: null,
		paymentIntentState: "idle",
		depositAmount: 0,
		mpesaPhone: "",
		manualAmountTendered: 0,
		manualReferenceNo: "",
		paymentProgress: PAYMENT_PROGRESS.IDLE,
		statusMessage: "",
		hostedPaymentUrl: "",
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
		activeMethods(state) {
			if (state.selectedPaymentChannel === PAYMENT_CHANNELS.OFFLINE) {
				return state.offlineMethods;
			}
			if (state.selectedPaymentChannel === PAYMENT_CHANNELS.ONLINE) {
				return state.onlineMethods;
			}
			return [];
		},
		selectedMethod(state) {
			return (
				this.activeMethods.find((method) => method.id === state.selectedMethodId) || null
			);
		},
		payableAmount(state) {
			const outstanding = Number(state.summary.payment.outstandingAmount || 0);
			if (state.selectedPaymentType === PAYMENT_TYPES.FULL) {
				return outstanding;
			}

			const minimumDue = Number(state.summary.payment.minimumDue || 0);
			const safeDeposit = clamp(
				Number(state.depositAmount || minimumDue),
				minimumDue,
				outstanding
			);
			return safeDeposit;
		},
		remainingAfterPayment(state) {
			const outstanding = Number(state.summary.payment.outstandingAmount || 0);
			const payable = this.payableAmount;
			return Math.max(0, outstanding - payable);
		},
		canConfirmWithoutPayment(state) {
			return Boolean(state.summary.payment.canConfirmWithoutPayment);
		},
		appliedCoupon(state) {
			const bookingCoupon = state.summary.pricing.bookingCoupon;
			if (bookingCoupon) {
				return {
					...bookingCoupon,
					coupon: bookingCoupon.code || bookingCoupon.name || "",
					discountAmount: Number(state.summary.pricing.bookingDiscountAmount || 0),
				};
			}
			return (
				state.summary.pricing.appointmentCoupons?.[0] ||
				state.summary.coupon.appliedCoupons?.[0] ||
				null
			);
		},
		totalSavings(state) {
			return Number(
				state.summary.pricing.appointmentDiscountTotal +
					state.summary.pricing.bookingDiscountAmount
			);
		},
		validationIssues(state) {
			const issues = [];
			if (!state.bookingId) {
				issues.push(
					"Booking reference is missing. Go back to assignments and continue again."
				);
			}
			if (!state.selectedPaymentChannel) {
				issues.push("Select a payment channel: Offline or Online.");
			}
			if (!state.selectedMethodId) {
				issues.push("Select a payment method to proceed.");
			}
			if (this.payableAmount <= 0) {
				issues.push("There is no payable amount for this booking.");
			}
			if (
				state.selectedPaymentType === PAYMENT_TYPES.DEPOSIT &&
				Number(state.depositAmount || 0) < Number(state.summary.payment.minimumDue || 0)
			) {
				issues.push("Deposit amount is below the minimum required confirmation amount.");
			}
			if (state.isApplyingCoupon || state.isValidatingCoupon) {
				issues.push("Wait for coupon processing to finish before taking payment.");
			}
			if (this.selectedMethod?.providerType === "mpesa" && !state.mpesaPhone) {
				issues.push("Phone number is required to trigger Mpesa STK push.");
			}
			if (
				state.selectedPaymentChannel === PAYMENT_CHANNELS.OFFLINE &&
				this.selectedMethod?.type === "online"
			) {
				issues.push("Online gateway cannot be used in Offline payment channel.");
			}
			if (
				state.selectedPaymentChannel === PAYMENT_CHANNELS.ONLINE &&
				this.selectedMethod?.type === "offline"
			) {
				issues.push("Offline mode of payment cannot be used in Online payment channel.");
			}
			return issues;
		},
		canSubmit() {
			return this.validationIssues.length === 0 && !this.isSubmitting;
		},
	},
	actions: {
		reset() {
			this.summary = createEmptyCheckoutSummary();
			this.couponDraft = "";
			this.couponValidation = null;
			this.couponMessage = "";
			this.couponError = "";
			this.isValidatingCoupon = false;
			this.isApplyingCoupon = false;
			this.selectedPaymentChannel = "";
			this.offlineMethods = [];
			this.onlineMethods = [];
			this.selectedPaymentType = PAYMENT_TYPES.FULL;
			this.selectedMethodId = "";
			this.paymentModeType = "";
			this.paymentGatewaySession = null;
			this.paymentIntentState = "idle";
			this.depositAmount = 0;
			this.mpesaPhone = "";
			this.manualAmountTendered = 0;
			this.manualReferenceNo = "";
			this.paymentProgress = PAYMENT_PROGRESS.IDLE;
			this.statusMessage = "";
			this.hostedPaymentUrl = "";
			this.isLoading = false;
			this.isSubmitting = false;
			this.error = "";
		},
		hydrateBookingContext(providedBookingId = "") {
			const workflowStore = useBookingWorkflowStore();
			workflowStore.hydrateFromStorage();
			this.bookingId = providedBookingId || workflowStore.bookingId || "";
			if (!this.mpesaPhone) {
				this.mpesaPhone = workflowStore.customerSnapshot?.mobileNo || "";
			}
		},
		setPaymentType(paymentType) {
			this.selectedPaymentType = paymentType;
			if (paymentType === PAYMENT_TYPES.FULL) {
				this.depositAmount = 0;
				return;
			}

			const minimumDue = Number(this.summary.payment.minimumDue || 0);
			this.depositAmount = minimumDue;
		},
		setSelectedMethod(methodId) {
			this.selectedMethodId = methodId;
			this.paymentModeType = this.selectedMethod?.sourceType || "";
			this.hostedPaymentUrl = "";
			this.paymentGatewaySession = null;
			this.statusMessage = "";
		},
		setPaymentChannel(channel) {
			this.selectedPaymentChannel = channel;
			this.selectedMethodId = "";
			this.paymentModeType = "";
			this.hostedPaymentUrl = "";
			this.paymentGatewaySession = null;
			this.statusMessage = "";
			this.paymentIntentState = "idle";
		},
		setDepositAmount(amount) {
			this.depositAmount = Number(amount || 0);
		},
		setMpesaPhone(phoneNumber) {
			this.mpesaPhone = phoneNumber;
		},
		setManualAmountTendered(value) {
			this.manualAmountTendered = Number(value || 0);
		},
		setManualReferenceNo(value) {
			this.manualReferenceNo = value || "";
		},
		setCouponDraft(value) {
			this.couponDraft = String(value || "")
				.trim()
				.toUpperCase();
			this.couponError = "";
			this.couponMessage = "";
		},
		syncSummary(summary) {
			this.summary = summary || createEmptyCheckoutSummary();
			if (this.selectedPaymentType === PAYMENT_TYPES.DEPOSIT) {
				this.depositAmount = Number(this.summary.payment.minimumDue || 0);
			}
		},
		async initializeCheckout(providedBookingId = "") {
			this.hydrateBookingContext(providedBookingId);
			if (!this.bookingId) {
				this.error = "Draft booking reference is missing.";
				return;
			}

			this.isLoading = true;
			this.error = "";

			try {
				const [summary, offlinePayload, onlinePayload] = await Promise.all([
					fetchCheckoutSummary(this.bookingId),
					fetchOfflinePaymentMethods(this.bookingId),
					fetchOnlinePaymentGateways(this.bookingId),
				]);

				this.syncSummary(summary);
				this.offlineMethods = offlinePayload.methods;
				this.onlineMethods = onlinePayload.methods;
				this.selectedPaymentChannel = "";
				this.selectedMethodId = "";
				this.paymentModeType = "";
				this.paymentGatewaySession = null;
				this.paymentIntentState = "idle";
				this.depositAmount = Number(summary.payment.minimumDue || 0);
				const bookingCoupon = summary.pricing.bookingCoupon;
				this.couponDraft = bookingCoupon?.code || bookingCoupon?.name || "";
			} catch (error) {
				this.error = error?.message || "Checkout could not be initialized.";
			} finally {
				this.isLoading = false;
			}
		},
		async refreshSummary() {
			if (!this.bookingId) return;
			try {
				const summary = await fetchCheckoutSummary(this.bookingId);
				this.syncSummary(summary);
			} catch (error) {
				this.error = error?.message || "Checkout summary could not be refreshed.";
			}
		},
		async validateCoupon(code) {
			if (!this.bookingId) return null;
			const value = String(code ?? this.couponDraft ?? "")
				.trim()
				.toUpperCase();
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
				console.log(
					"DEBUG(validateCoupon): bookingId:",
					this.bookingId,
					"coupon:",
					value,
					"validation:",
					validation
				);
				if (!validation.valid) {
					this.couponError =
						validation.message || "Coupon is not valid for this booking.";
				}
				return validation;
			} catch (error) {
				this.couponValidation = null;
				this.couponError = error?.message || "Coupon validation failed.";
				return null;
			} finally {
				this.isValidatingCoupon = false;
			}
		},
		async applyCoupon(code) {
			if (!this.bookingId) return;
			const value = String(code ?? this.couponDraft ?? "")
				.trim()
				.toUpperCase();
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
				this.syncSummary(response.checkout);
				this.couponDraft = value;
				this.couponValidation = validation;
				this.couponMessage = response.message || "Coupon applied successfully.";
				this.hostedPaymentUrl = "";
				this.paymentGatewaySession = null;
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
			} catch (error) {
				this.couponError = error?.message || "Coupon could not be applied.";
			} finally {
				this.isApplyingCoupon = false;
			}
		},
		async removeCoupon() {
			if (!this.bookingId) return;
			const couponCode =
				this.summary.pricing.bookingCoupon?.code ||
				this.summary.pricing.bookingCoupon?.name ||
				this.couponDraft ||
				"";

			this.isApplyingCoupon = true;
			this.couponError = "";
			this.couponMessage = "";

			try {
				const response = await removeCheckoutCoupon(
					this.bookingId,
					couponCode || undefined
				);
				this.syncSummary(response.checkout);
				this.couponDraft = "";
				this.couponValidation = null;
				this.couponMessage = response.message || "Coupon removed.";
				this.hostedPaymentUrl = "";
				this.paymentGatewaySession = null;
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
			} catch (error) {
				this.couponError = error?.message || "Coupon could not be removed.";
			} finally {
				this.isApplyingCoupon = false;
			}
		},
		async triggerGatewayPayment({ redirectTo = "" } = {}) {
			if (this.selectedPaymentChannel !== PAYMENT_CHANNELS.ONLINE) {
				throw new Error("Select Online payment channel for gateway checkout.");
			}
			if (!this.selectedMethod?.gateway) {
				throw new Error("Gateway payment method is not selected.");
			}

			this.isSubmitting = true;
			this.error = "";
			this.paymentProgress = PAYMENT_PROGRESS.PROCESSING;
			this.paymentIntentState = "processing";
			this.statusMessage = "Initiating payment gateway request...";

			try {
				const paymentType = this.selectedPaymentType;
				const amount = Number(this.payableAmount || 0);

				const payload = await createHostedCheckoutPayment({
					bookingId: this.bookingId,
					paymentGateway: this.selectedMethod.gateway,
					redirectTo,
					phoneNumber:
						this.selectedMethod.providerType === "mpesa" ? this.mpesaPhone : "",
					amount,
					paymentType,
					couponCode:
						this.summary.pricing.bookingCoupon?.code ||
						this.summary.pricing.bookingCoupon?.name ||
						"",
					finalAmountReference: Number(this.summary.pricing.finalAmount || 0),
				});

				this.hostedPaymentUrl = payload?.url || "";
				this.paymentGatewaySession = payload || null;
				if (payload?.checkout) {
					this.syncSummary(payload.checkout);
					invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
					invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				}

				if (this.selectedMethod.providerType === "mpesa") {
					this.paymentProgress = PAYMENT_PROGRESS.AWAITING_CONFIRMATION;
					this.paymentIntentState = "awaiting_confirmation";
					this.statusMessage = "Mpesa STK push sent. Waiting for customer confirmation.";
				} else {
					this.paymentProgress = PAYMENT_PROGRESS.SUCCESS;
					this.paymentIntentState = "success";
					this.statusMessage = "Payment link generated successfully.";
				}

				return payload;
			} catch (error) {
				this.paymentProgress = PAYMENT_PROGRESS.FAILED;
				this.paymentIntentState = "failed";
				this.error = error?.message || "Payment could not be initiated.";
				throw error;
			} finally {
				this.isSubmitting = false;
			}
		},
		async recordManualPayment() {
			if (this.selectedPaymentChannel !== PAYMENT_CHANNELS.OFFLINE) {
				throw new Error("Select Offline payment channel to record manual payment.");
			}
			this.isSubmitting = true;
			this.error = "";
			this.paymentProgress = PAYMENT_PROGRESS.PROCESSING;
			this.paymentIntentState = "processing";
			this.statusMessage = "Recording manual payment...";

			try {
				const payload = await recordManualCheckoutPayment({
					bookingId: this.bookingId,
					amount: this.payableAmount,
					modeOfPayment: this.selectedMethod?.modeOfPayment || "",
					referenceNo: this.manualReferenceNo,
				});

				if (payload?.checkout) {
					this.summary = payload.checkout;
					invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
					invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				}

				this.paymentProgress = PAYMENT_PROGRESS.SUCCESS;
				this.paymentIntentState = "success";
				this.statusMessage = "Payment recorded successfully.";
				return payload;
			} catch (error) {
				this.paymentProgress = PAYMENT_PROGRESS.FAILED;
				this.paymentIntentState = "failed";
				this.error = error?.message || "Manual payment could not be recorded.";
				throw error;
			} finally {
				this.isSubmitting = false;
			}
		},
		async confirmWithoutPayment() {
			if (!this.canConfirmWithoutPayment) {
				throw new Error("Booking cannot be confirmed without payment.");
			}

			this.isSubmitting = true;
			this.error = "";
			this.paymentProgress = PAYMENT_PROGRESS.PROCESSING;
			this.paymentIntentState = "processing";
			this.statusMessage = "Confirming booking without payment...";

			try {
				const payload = await confirmCheckoutWithoutPayment(this.bookingId);
				if (payload?.checkout) {
					this.summary = payload.checkout;
					invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
					invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				}

				this.paymentProgress = PAYMENT_PROGRESS.SUCCESS;
				this.paymentIntentState = "success";
				this.statusMessage = "Booking confirmed without payment.";
				return payload;
			} catch (error) {
				this.paymentProgress = PAYMENT_PROGRESS.FAILED;
				this.paymentIntentState = "failed";
				this.error = error?.message || "Booking could not be confirmed without payment.";
				throw error;
			} finally {
				this.isSubmitting = false;
			}
		},
	},
});
