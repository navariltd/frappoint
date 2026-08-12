import { defineStore } from "pinia";
import {
	createDraftServiceBooking,
	reloadDraftServiceBooking,
	updateDraftServiceAppointmentNotes,
	upsertDraftCoupleAppointments,
	upsertDraftServiceAppointment,
} from "@/services/bookingOrchestration.service";
import { BOOKING_WORKFLOW_STORAGE_KEY, createEmptyDraftBooking } from "@/types/booking";
import { CACHE_MAX_AGE, CACHE_TAGS, invalidateMemoryCacheByTag } from "@/utils/cachePolicy";

const canUseStorage = () => typeof window !== "undefined" && Boolean(window.localStorage);

const coupleSlotForGuest = (candidate, guestNumber) => {
	const leg = guestNumber === 1 ? candidate.guest1 : candidate.guest2;
	return {
		id: `${candidate.id}:guest-${guestNumber}`,
		candidateId: candidate.candidateId || candidate.id,
		date: candidate.date,
		startTime: leg.startTime || candidate.startTime,
		endTime: leg.endTime,
		duration: Number(leg.duration || 0),
		availability: "available",
		assignedProvider: leg.provider,
		assignedProviderName: leg.providerName,
		providerSummary: leg.providerName || leg.provider || "Auto-assigned",
		providers: [
			{
				provider: leg.provider,
				providerName: leg.providerName,
				serviceUnit: leg.serviceUnit,
				serviceUnitName: leg.serviceUnitName,
				slotIds: leg.slotIds || [],
			},
		],
		serviceUnit: leg.serviceUnit,
		bufferBefore: leg.bufferBefore,
		bufferAfter: leg.bufferAfter,
		isCouple: true,
	};
};

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
		async createDraftBookingSession({
			customer,
			customerSummary,
			cartItems,
			bookedBy,
			isCouple = false,
			coupleServiceKeys = [],
		}) {
			this.isCreatingBooking = true;
			this.bookingError = "";

			try {
				const booking = await createDraftServiceBooking({
					customer,
					customerSummary,
					cartItems,
					bookedBy,
					isCouple,
					coupleServiceKeys,
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
					isCouple: this.draftBooking.isCouple,
					coupleServiceKeys: this.draftBooking.coupleServiceKeys,
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
							notes: guest.notes || "",
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
		async upsertDraftCouple({ primary, secondary, slot }) {
			if (!this.draftBooking.id) {
				const error = new Error("Create a draft booking before reserving appointments.");
				this.bookingError = error.message;
				throw error;
			}

			const pairs = [primary, secondary];
			const guestKeys = pairs.map((pair) => pair.guest.guestKey);
			const busyState = Object.fromEntries(guestKeys.map((guestKey) => [guestKey, true]));
			const clearErrors = Object.fromEntries(guestKeys.map((guestKey) => [guestKey, ""]));
			this.isSavingAppointmentByGuest = {
				...this.isSavingAppointmentByGuest,
				...busyState,
			};
			this.appointmentErrorByGuest = {
				...this.appointmentErrorByGuest,
				...clearErrors,
			};

			const pairsWithAppointmentIds = pairs.map((pair) => ({
				...pair,
				guest: {
					...pair.guest,
					appointmentId:
						pair.guest.appointmentId ||
						this.appointmentsByGuestKey[pair.guest.guestKey]?.appointmentId ||
						"",
				},
			}));

			try {
				const result = await upsertDraftCoupleAppointments({
					bookingId: this.draftBooking.id,
					primary: pairsWithAppointmentIds[0],
					secondary: pairsWithAppointmentIds[1],
					slot,
				});
				const appointmentRows = [result.primaryAppointment, result.secondaryAppointment];
				const appointmentUpdates = {};
				pairsWithAppointmentIds.forEach((pair, index) => {
					const appointment = appointmentRows[index] || {};
					const guestSlot = coupleSlotForGuest(slot, index + 1);
					appointmentUpdates[pair.guest.guestKey] = {
						appointmentId:
							appointment.name ||
							appointment.appointmentId ||
							pair.guest.appointmentId ||
							"",
						guestKey: pair.guest.guestKey,
						serviceKey: pair.service.serviceKey,
						serviceId: pair.service.serviceId,
						date: slot.date,
						slot: guestSlot,
						guest: {
							fullName: pair.guest.fullName,
							email: pair.guest.email || "",
							mobileNo: pair.guest.mobileNo || "",
							notes: pair.guest.notes || "",
							providerGender: pair.guest.providerGender || "",
							providerPreference: pair.guest.providerPreference || "",
						},
						isCouple: true,
						isPrimaryInCouple: index === 0,
						coupleAppointmentId:
							appointment.coupleAppointmentId ||
							appointment.couple_appointment_id ||
							appointmentRows[index === 0 ? 1 : 0]?.name ||
							"",
					};
				});

				this.draftBooking = {
					...this.draftBooking,
					...result.booking,
					isCouple: true,
					coupleServiceKeys: this.draftBooking.coupleServiceKeys,
					cartItemsSnapshot: this.draftBooking.cartItemsSnapshot,
					customerSnapshot: this.draftBooking.customerSnapshot,
				};
				this.appointmentsByGuestKey = {
					...this.appointmentsByGuestKey,
					...appointmentUpdates,
				};
				this.hydrationRequiresRevalidation = false;
				this.hydratedAt = Date.now();
				this.persistState();
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				invalidateMemoryCacheByTag(CACHE_TAGS.WORKFLOW);

				return {
					...result,
					slotsByGuestKey: Object.fromEntries(
						guestKeys.map((guestKey, index) => [
							guestKey,
							appointmentUpdates[guestKey].slot,
						])
					),
				};
			} catch (error) {
				const message =
					error?.message || "Both appointments could not be reserved together.";
				this.appointmentErrorByGuest = {
					...this.appointmentErrorByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, message])),
				};
				throw error;
			} finally {
				this.isSavingAppointmentByGuest = {
					...this.isSavingAppointmentByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, false])),
				};
			}
		},
		async updateAppointmentNotes({ guestKey, appointmentId, notes }) {
			const existing = this.appointmentsByGuestKey[guestKey] || {};
			const resolvedAppointmentId = appointmentId || existing.appointmentId;
			if (!resolvedAppointmentId) {
				this.appointmentsByGuestKey = {
					...this.appointmentsByGuestKey,
					[guestKey]: {
						...existing,
						guestKey,
						guest: {
							...(existing.guest || {}),
							notes: notes || "",
						},
					},
				};
				this.persistState();
				return null;
			}

			const appointment = await updateDraftServiceAppointmentNotes({
				appointmentId: resolvedAppointmentId,
				notes,
			});
			this.appointmentsByGuestKey = {
				...this.appointmentsByGuestKey,
				[guestKey]: {
					...existing,
					appointmentId: resolvedAppointmentId,
					guestKey,
					guest: {
						...(existing.guest || {}),
						notes: notes || "",
					},
				},
			};
			this.persistState();
			invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
			invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
			invalidateMemoryCacheByTag(CACHE_TAGS.WORKFLOW);
			return appointment;
		},
	},
});
