import { defineStore } from "pinia";
import {
	createDraftServiceBooking,
	reloadDraftServiceBooking,
	upsertDraftServiceAppointment,
} from "@/services/bookingOrchestration.service";
import { BOOKING_WORKFLOW_STORAGE_KEY, createEmptyDraftBooking } from "@/types/booking";
import { CACHE_MAX_AGE, CACHE_TAGS, invalidateMemoryCacheByTag } from "@/utils/cachePolicy";

const canUseStorage = () => typeof window !== "undefined" && Boolean(window.localStorage);

const createInitialState = () => ({
	hasHydrated: false,
	draftBooking: createEmptyDraftBooking(),
	appointmentsByGuestKey: {},
	isCreatingBooking: false,
	isHydratingBooking: false,
	isSavingAppointmentByGuest: {},
	bookingError: "",
	appointmentErrorByGuest: {},
	hydratedAt: 0,
	workflowMaxAge: CACHE_MAX_AGE.WORKFLOW_STATE,
	hydrationRequiresRevalidation: false,
});

export const useBookingWorkflowStore = defineStore("bookingWorkflow", {
	state: createInitialState,
	getters: {
		bookingId(state) {
			return state.draftBooking.id || "";
		},
		hasDraftBooking(state) {
			return Boolean(state.draftBooking.id);
		},
		cartItemsSnapshot(state) {
			return state.draftBooking.cartItemsSnapshot || [];
		},
		customerSnapshot(state) {
			return state.draftBooking.customerSnapshot || null;
		},
	},
	actions: {
		persistState() {
			if (!canUseStorage()) return;
			window.localStorage.setItem(
				BOOKING_WORKFLOW_STORAGE_KEY,
				JSON.stringify({
					persistedAt: Date.now(),
					maxAge: this.workflowMaxAge,
					draftBooking: this.draftBooking,
					appointmentsByGuestKey: this.appointmentsByGuestKey,
				})
			);
		},
		hydrateFromStorage() {
			if (this.hasHydrated || !canUseStorage()) {
				this.hasHydrated = true;
				return;
			}

			const raw = window.localStorage.getItem(BOOKING_WORKFLOW_STORAGE_KEY);
			if (!raw) {
				this.hasHydrated = true;
				return;
			}

			try {
				const parsed = JSON.parse(raw);
				const persistedAt = Number(parsed?.persistedAt || 0);
				const maxAge = Number(parsed?.maxAge || this.workflowMaxAge);
				const isExpired = !persistedAt || Date.now() - persistedAt > maxAge;

				if (isExpired) {
					window.localStorage.removeItem(BOOKING_WORKFLOW_STORAGE_KEY);
					this.draftBooking = createEmptyDraftBooking();
					this.appointmentsByGuestKey = {};
					this.hydratedAt = 0;
					this.hydrationRequiresRevalidation = false;
					this.hasHydrated = true;
					return;
				}

				this.draftBooking = parsed?.draftBooking || createEmptyDraftBooking();
				this.appointmentsByGuestKey = parsed?.appointmentsByGuestKey || {};
				this.hydratedAt = persistedAt;
				this.hydrationRequiresRevalidation = Boolean(this.draftBooking?.id);
			} catch {
				this.draftBooking = createEmptyDraftBooking();
				this.appointmentsByGuestKey = {};
				this.hydratedAt = 0;
				this.hydrationRequiresRevalidation = false;
			}

			this.hasHydrated = true;
		},
		clearWorkflow() {
			Object.assign(this, createInitialState(), { hasHydrated: true });
			if (canUseStorage()) {
				window.localStorage.removeItem(BOOKING_WORKFLOW_STORAGE_KEY);
			}
			invalidateMemoryCacheByTag(CACHE_TAGS.WORKFLOW);
			invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
			invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
		},
		clearBookingError() {
			this.bookingError = "";
		},
		clearAppointmentError(guestKey) {
			this.appointmentErrorByGuest = {
				...this.appointmentErrorByGuest,
				[guestKey]: "",
			};
		},
		async createDraftBookingSession({ customer, customerSummary, cartItems }) {
			this.isCreatingBooking = true;
			this.bookingError = "";

			try {
				const booking = await createDraftServiceBooking({
					customer,
					customerSummary,
					cartItems,
				});
				this.draftBooking = booking;
				this.appointmentsByGuestKey = {};
				this.hydrationRequiresRevalidation = false;
				this.hydratedAt = Date.now();
				this.persistState();
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				invalidateMemoryCacheByTag(CACHE_TAGS.WORKFLOW);
				return booking;
			} catch (error) {
				this.bookingError = error?.message || "Draft booking could not be created.";
				throw error;
			} finally {
				this.isCreatingBooking = false;
			}
		},
		async reloadDraftBookingSession() {
			if (!this.draftBooking.id) {
				return null;
			}

			this.isHydratingBooking = true;
			this.bookingError = "";

			try {
				const booking = await reloadDraftServiceBooking({
					bookingId: this.draftBooking.id,
					cartItems: this.draftBooking.cartItemsSnapshot,
					customer: this.draftBooking.customerSnapshot,
				});
				this.draftBooking = {
					...booking,
					cartItemsSnapshot: this.draftBooking.cartItemsSnapshot,
					customerSnapshot: this.draftBooking.customerSnapshot,
				};
				this.hydrationRequiresRevalidation = false;
				this.hydratedAt = Date.now();
				this.persistState();
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				return booking;
			} catch (error) {
				this.bookingError = error?.message || "Draft booking could not be loaded.";
				throw error;
			} finally {
				this.isHydratingBooking = false;
			}
		},
		async upsertDraftAppointment({ guestKey, service, guest, date, slot }) {
			if (!this.draftBooking.id) {
				const error = new Error("Create a draft booking before reserving appointments.");
				this.bookingError = error.message;
				throw error;
			}

			const existing = this.appointmentsByGuestKey[guestKey];
			this.isSavingAppointmentByGuest = {
				...this.isSavingAppointmentByGuest,
				[guestKey]: true,
			};
			this.appointmentErrorByGuest = {
				...this.appointmentErrorByGuest,
				[guestKey]: "",
			};

			try {
				const result = await upsertDraftServiceAppointment({
					bookingId: this.draftBooking.id,
					appointmentId: existing?.appointmentId,
					service,
					guest,
					date,
					slot,
				});

				this.draftBooking = {
					...this.draftBooking,
					...result.booking,
					cartItemsSnapshot: this.draftBooking.cartItemsSnapshot,
					customerSnapshot: this.draftBooking.customerSnapshot,
				};
				this.appointmentsByGuestKey = {
					...this.appointmentsByGuestKey,
					[guestKey]: {
						appointmentId: result.appointment?.name || existing?.appointmentId || "",
						guestKey,
						serviceKey: service.serviceKey,
						serviceId: service.serviceId,
						date,
						slot,
						guest: {
							fullName: guest.fullName,
							email: guest.email || "",
							mobileNo: guest.mobileNo || "",
							providerGender: guest.providerGender || "",
							providerPreference: guest.providerPreference || "",
						},
					},
				};
				this.hydrationRequiresRevalidation = false;
				this.hydratedAt = Date.now();
				this.persistState();
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				invalidateMemoryCacheByTag(CACHE_TAGS.WORKFLOW);
				return result;
			} catch (error) {
				this.appointmentErrorByGuest = {
					...this.appointmentErrorByGuest,
					[guestKey]: error?.message || "Appointment could not be reserved.",
				};
				throw error;
			} finally {
				this.isSavingAppointmentByGuest = {
					...this.isSavingAppointmentByGuest,
					[guestKey]: false,
				};
			}
		},
	},
});
