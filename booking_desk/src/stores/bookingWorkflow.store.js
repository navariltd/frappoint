import { defineStore } from "pinia";
import {
	createDraftServiceBooking,
	reloadDraftServiceBooking,
	upsertDraftServiceAppointment,
} from "@/services/bookingOrchestration.service";
import { BOOKING_WORKFLOW_STORAGE_KEY, createEmptyDraftBooking } from "@/types/booking";

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
				this.draftBooking = parsed?.draftBooking || createEmptyDraftBooking();
				this.appointmentsByGuestKey = parsed?.appointmentsByGuestKey || {};
			} catch {
				this.draftBooking = createEmptyDraftBooking();
				this.appointmentsByGuestKey = {};
			}

			this.hasHydrated = true;
		},
		clearWorkflow() {
			Object.assign(this, createInitialState(), { hasHydrated: true });
			if (canUseStorage()) {
				window.localStorage.removeItem(BOOKING_WORKFLOW_STORAGE_KEY);
			}
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
				this.persistState();
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
				this.persistState();
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
						},
					},
				};
				this.persistState();
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
