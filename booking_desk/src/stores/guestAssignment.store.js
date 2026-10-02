import { defineStore } from "pinia";
import {
	buildAssignmentsFromCart,
	buildValidationIssues,
	getAssignmentProgress,
	summarizeAssignments,
} from "@/services/guestAssignment.service";
import {
	fetchNormalizedAvailableDates,
	fetchNormalizedAvailableSlots,
	fetchNormalizedCoupleAvailableDates,
	fetchNormalizedCoupleAvailableSlots,
} from "@/services/availability.service";
import { fetchServicePackages } from "@/services/services.service";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";

const findServiceIndex = (assignments, serviceKey) =>
	assignments.findIndex((service) => service.serviceKey === serviceKey);

const findGuestIndex = (service, guestKey) =>
	service.guests.findIndex((guest) => guest.guestKey === guestKey);

const syncGuestCompletion = (guest) => {
	guest.isComplete = Boolean(guest.fullName && guest.date && guest.slot);
};

const getCoupleEntries = (assignments) =>
	assignments
		.flatMap((service) => service.guests.map((guest) => ({ service, guest })))
		.sort(
			(a, b) =>
				Number(a.guest.coupleSequence || Number.MAX_SAFE_INTEGER) -
				Number(b.guest.coupleSequence || Number.MAX_SAFE_INTEGER)
		)
		.slice(0, 2);

const toAppointmentService = (service) => ({
	serviceKey: service.serviceKey,
	serviceId: service.serviceId,
	serviceName: service.serviceName,
	pricingModel: service.pricingModel,
	packageName: service.packageName,
	packageId: service.packageId,
	price: service.price,
	currency: service.currency,
	duration: service.duration,
});

export const useGuestAssignmentStore = defineStore("guestAssignment", {
	state: () => ({
		assignments: [],
		activeServiceIndex: 0,
		activeGuestIndex: 0,
		isLoadingDates: {},
		isLoadingSlots: {},
		isReservingSlots: {},
		reservingSlotIdByGuest: {},
		errorByGuest: {},
		customers: [],
		selectedCustomerId: "",
		selectedCustomer: null,
		isCoupleMode: false,
		coupleAvailableDates: [],
		coupleAvailableSlots: [],
		coupleSelectedDate: "",
		coupleError: "",
		coupleAvailabilityRequestToken: 0,
	}),
	getters: {
		progress(state) {
			return getAssignmentProgress(state.assignments);
		},
		validationIssues(state) {
			return buildValidationIssues(state.assignments, {
				isCouple: state.isCoupleMode,
			});
		},
		isComplete() {
			return this.validationIssues.length === 0 && this.progress.totalGuests > 0;
		},
		summaryRows(state) {
			return summarizeAssignments(state.assignments);
		},
		coupleEntries(state) {
			return getCoupleEntries(state.assignments);
		},
	},
	actions: {
		initialize({
			cartItems = [],
			customers = [],
			selectedCustomerId = "",
			selectedCustomer = null,
			appointmentsByGuestKey = {},
			isCoupleMode = false,
		}) {
			this.customers = customers;
			this.selectedCustomerId = selectedCustomerId;
			const resolvedSelectedCustomer =
				selectedCustomer ||
				customers.find((item) => item.id === selectedCustomerId) ||
				null;
			this.assignments = buildAssignmentsFromCart(
				cartItems,
				resolvedSelectedCustomer,
				appointmentsByGuestKey
			);
			this.isCoupleMode = Boolean(isCoupleMode);
			if (this.isCoupleMode) {
				getCoupleEntries(this.assignments).forEach(({ guest }, index) => {
					guest.coupleSequence = index + 1;
					if (
						index === 1 &&
						!guest.appointmentId &&
						!guest.isInlineGuest &&
						guest.customerId === resolvedSelectedCustomer?.id
					) {
						guest.customerId = "";
						guest.fullName = "";
						guest.email = "";
						guest.mobileNo = "";
						guest.isInlineGuest = true;
					}
				});
			}
			this.activeServiceIndex = 0;
			this.activeGuestIndex = 0;
			this.isLoadingDates = {};
			this.isLoadingSlots = {};
			this.isReservingSlots = {};
			this.reservingSlotIdByGuest = {};
			this.errorByGuest = {};
			this.coupleAvailableDates = [];
			this.coupleAvailableSlots = [];
			this.coupleAvailabilityRequestToken += 1;
			this.coupleSelectedDate = getCoupleEntries(this.assignments)[0]?.guest.date || "";
			this.coupleError = "";
		},
		setActiveIndices(serviceIndex, guestIndex) {
			this.activeServiceIndex = serviceIndex;
			this.activeGuestIndex = guestIndex;
		},
		updateGuestFromCustomer(serviceKey, guestKey, customerId) {
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;
			const customer = this.customers.find((item) => item.id === customerId);
			if (!customer) return;

			const guest = service.guests[guestIndex];
			guest.customerId = customer.id;
			guest.fullName = customer.name;
			guest.isInlineGuest = false;
			if (this.isCoupleMode) {
				this.clearCoupleSchedule();
				return;
			}
			syncGuestCompletion(guest);
		},
		quickCreateGuest(serviceKey, guestKey, payload) {
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;

			const guest = service.guests[guestIndex];
			guest.customerId = "";
			guest.fullName = payload.fullName || "";
			guest.email = payload.email || "";
			guest.mobileNo = payload.mobileNo || "";
			guest.providerGender = payload.providerGender || "";
			guest.providerPreference =
				payload.providerPreference || guest.providerPreference || "";
			guest.isInlineGuest = true;
			if (this.isCoupleMode) {
				this.clearCoupleSchedule();
				return;
			}
			syncGuestCompletion(guest);
		},
		clearGuest(serviceKey, guestKey) {
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;
			if (service.guests[guestIndex].appointmentId) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]:
						"Reserved appointments cannot be cleared yet. Pick a new date or slot to update the reservation.",
				};
				return;
			}

			service.guests[guestIndex] = {
				...service.guests[guestIndex],
				appointmentId: "",
				customerId: "",
				fullName: "",
				email: "",
				mobileNo: "",
				notes: "",
				isInlineGuest: false,
				providerGender: "",
				providerPreference: "",
				date: "",
				slot: null,
				availableDates: [],
				availableSlots: [],
				isComplete: false,
			};
		},
		async fetchGuestDates(serviceKey, guestKey) {
			if (this.isCoupleMode) {
				return this.fetchCoupleDates();
			}
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;

			this.isLoadingDates = { ...this.isLoadingDates, [guestKey]: true };
			this.errorByGuest = { ...this.errorByGuest, [guestKey]: "" };
			try {
				await this.ensureServiceProviders(serviceKey);
				const dates = await fetchNormalizedAvailableDates({
					serviceType: service.serviceId,
					duration: service.duration,
					provider: service.guests[guestIndex].providerPreference,
					gender: service.guests[guestIndex].providerGender,
				});
				service.guests[guestIndex].availableDates = dates;
			} catch (error) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]: error?.message || "Failed to load available dates.",
				};
			} finally {
				this.isLoadingDates = { ...this.isLoadingDates, [guestKey]: false };
			}
		},
		async selectGuestDate(serviceKey, guestKey, date) {
			if (this.isCoupleMode) {
				return this.selectCoupleDate(date);
			}
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;

			const guest = service.guests[guestIndex];
			guest.date = date;
			guest.slot = null;
			guest.availableSlots = [];
			syncGuestCompletion(guest);

			this.isLoadingSlots = { ...this.isLoadingSlots, [guestKey]: true };
			this.errorByGuest = { ...this.errorByGuest, [guestKey]: "" };

			try {
				const slots = await fetchNormalizedAvailableSlots({
					serviceType: service.serviceId,
					duration: service.duration,
					provider: guest.providerPreference,
					gender: guest.providerGender,
					date,
				});
				guest.availableSlots = slots;
			} catch (error) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]: error?.message || "Failed to load available slots.",
				};
			} finally {
				this.isLoadingSlots = { ...this.isLoadingSlots, [guestKey]: false };
			}
		},
		async selectGuestSlot(serviceKey, guestKey, slotId) {
			if (this.isCoupleMode) {
				return this.selectCoupleSlot(slotId);
			}
			const workflowStore = useBookingWorkflowStore();
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;
			const guest = service.guests[guestIndex];
			const slot = guest.availableSlots.find((row) => row.id === slotId);
			if (!slot) return;

			this.isReservingSlots = { ...this.isReservingSlots, [guestKey]: true };
			this.reservingSlotIdByGuest = { ...this.reservingSlotIdByGuest, [guestKey]: slotId };
			this.errorByGuest = { ...this.errorByGuest, [guestKey]: "" };

			try {
				const result = await workflowStore.upsertDraftAppointment({
					guestKey,
					service: {
						serviceKey: service.serviceKey,
						serviceId: service.serviceId,
						serviceName: service.serviceName,
						pricingModel: service.pricingModel,
						packageName: service.packageName,
						packageId: service.packageId,
						price: service.price,
						currency: service.currency,
						duration: service.duration,
					},
					guest: {
						fullName: guest.fullName,
						email: guest.email,
						mobileNo: guest.mobileNo,
						providerGender: guest.providerGender,
						providerPreference: guest.providerPreference,
						notes: guest.notes,
					},
					date: guest.date,
					slot,
				});

				guest.slot = slot;
				guest.appointmentId = result?.appointment?.name || guest.appointmentId;
				syncGuestCompletion(guest);
				this.moveToNextPendingGuest();
			} catch (error) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]: error?.message || "Appointment could not be reserved.",
				};
			} finally {
				this.isReservingSlots = { ...this.isReservingSlots, [guestKey]: false };
				this.reservingSlotIdByGuest = { ...this.reservingSlotIdByGuest, [guestKey]: "" };
			}
		},
		moveToNextPendingGuest() {
			for (let s = 0; s < this.assignments.length; s += 1) {
				const service = this.assignments[s];
				for (let g = 0; g < service.guests.length; g += 1) {
					if (!service.guests[g].isComplete) {
						this.activeServiceIndex = s;
						this.activeGuestIndex = g;
						return;
					}
				}
			}
		},
		async ensureServiceProviders(serviceKey) {
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return [];
			const service = this.assignments[serviceIndex];
			if (Array.isArray(service.providerOptions) && service.providerOptions.length) {
				return service.providerOptions;
			}

			const details = await fetchServicePackages(service.serviceId, service.duration);
			service.providerOptions = Array.isArray(details.providers) ? details.providers : [];
			return service.providerOptions;
		},
		async updateProviderPreference(serviceKey, guestKey, providerId) {
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;

			await this.ensureServiceProviders(serviceKey);
			const guest = service.guests[guestIndex];
			guest.providerPreference = providerId || "";
			if (this.isCoupleMode) {
				this.clearCoupleSchedule();
				if (getCoupleEntries(this.assignments).every((entry) => entry.guest.fullName)) {
					await this.fetchCoupleDates();
				}
				return;
			}
			guest.date = "";
			guest.slot = null;
			guest.availableDates = [];
			guest.availableSlots = [];
			syncGuestCompletion(guest);

			if (guest.fullName) {
				await this.fetchGuestDates(serviceKey, guestKey);
			}
		},
		clearCoupleSchedule() {
			this.coupleAvailabilityRequestToken += 1;
			getCoupleEntries(this.assignments).forEach(({ guest }) => {
				guest.date = "";
				guest.slot = null;
				guest.availableDates = [];
				guest.availableSlots = [];
				syncGuestCompletion(guest);
			});
			this.coupleAvailableDates = [];
			this.coupleAvailableSlots = [];
			this.coupleSelectedDate = "";
			this.coupleError = "";
		},
		async fetchCoupleDates() {
			const entries = getCoupleEntries(this.assignments);
			if (entries.length !== 2) {
				this.coupleError = "Couple bookings require exactly two service assignments.";
				return [];
			}

			const requestToken = ++this.coupleAvailabilityRequestToken;
			const guestKeys = entries.map((entry) => entry.guest.guestKey);
			this.isLoadingDates = {
				...this.isLoadingDates,
				...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, true])),
			};
			this.coupleError = "";
			this.errorByGuest = {
				...this.errorByGuest,
				...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, ""])),
			};

			try {
				await Promise.all(
					Array.from(new Set(entries.map((entry) => entry.service.serviceKey))).map(
						(serviceKey) => this.ensureServiceProviders(serviceKey)
					)
				);
				const dates = await fetchNormalizedCoupleAvailableDates({
					serviceType1: entries[0].service.serviceId,
					serviceType2: entries[1].service.serviceId,
					duration1: entries[0].service.duration,
					duration2: entries[1].service.duration,
					provider1: entries[0].guest.providerPreference,
					provider2: entries[1].guest.providerPreference,
					excludeAppointmentId1: entries[0].guest.appointmentId,
					excludeAppointmentId2: entries[1].guest.appointmentId,
				});
				if (requestToken !== this.coupleAvailabilityRequestToken) return [];
				this.coupleAvailableDates = dates;
				entries.forEach(({ guest }) => {
					guest.availableDates = dates;
				});
				return dates;
			} catch (error) {
				if (requestToken !== this.coupleAvailabilityRequestToken) return [];
				const message = error?.message || "Failed to load couple availability.";
				this.coupleError = message;
				this.errorByGuest = {
					...this.errorByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, message])),
				};
				return [];
			} finally {
				if (requestToken === this.coupleAvailabilityRequestToken) {
					this.isLoadingDates = {
						...this.isLoadingDates,
						...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, false])),
					};
				}
			}
		},
		async selectCoupleDate(date) {
			const entries = getCoupleEntries(this.assignments);
			if (entries.length !== 2) return [];
			const requestToken = ++this.coupleAvailabilityRequestToken;
			const guestKeys = entries.map((entry) => entry.guest.guestKey);
			this.coupleSelectedDate = date;
			this.coupleAvailableSlots = [];
			entries.forEach(({ guest }) => {
				guest.date = date;
				guest.slot = null;
				guest.availableSlots = [];
				syncGuestCompletion(guest);
			});
			this.isLoadingSlots = {
				...this.isLoadingSlots,
				...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, true])),
			};
			this.coupleError = "";

			try {
				const slots = await fetchNormalizedCoupleAvailableSlots({
					serviceType1: entries[0].service.serviceId,
					serviceType2: entries[1].service.serviceId,
					duration1: entries[0].service.duration,
					duration2: entries[1].service.duration,
					provider1: entries[0].guest.providerPreference,
					provider2: entries[1].guest.providerPreference,
					excludeAppointmentId1: entries[0].guest.appointmentId,
					excludeAppointmentId2: entries[1].guest.appointmentId,
					date,
				});
				if (
					requestToken !== this.coupleAvailabilityRequestToken ||
					this.coupleSelectedDate !== date
				) {
					return [];
				}
				this.coupleAvailableSlots = slots;
				return slots;
			} catch (error) {
				if (requestToken !== this.coupleAvailabilityRequestToken) return [];
				const message = error?.message || "Failed to load simultaneous availability.";
				this.coupleError = message;
				this.errorByGuest = {
					...this.errorByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, message])),
				};
				return [];
			} finally {
				if (requestToken === this.coupleAvailabilityRequestToken) {
					this.isLoadingSlots = {
						...this.isLoadingSlots,
						...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, false])),
					};
				}
			}
		},
		async selectCoupleSlot(slotId) {
			const workflowStore = useBookingWorkflowStore();
			const entries = getCoupleEntries(this.assignments);
			const slot = this.coupleAvailableSlots.find((candidate) => candidate.id === slotId);
			if (entries.length !== 2 || !slot) return;
			if (!entries.every((entry) => entry.guest.fullName)) {
				this.coupleError = "Enter both guest names before reserving a couple slot.";
				return;
			}

			const guestKeys = entries.map((entry) => entry.guest.guestKey);
			this.isReservingSlots = {
				...this.isReservingSlots,
				...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, true])),
			};
			this.reservingSlotIdByGuest = {
				...this.reservingSlotIdByGuest,
				...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, slotId])),
			};
			this.coupleError = "";

			try {
				const result = await workflowStore.upsertDraftCouple({
					primary: {
						service: toAppointmentService(entries[0].service),
						guest: { ...entries[0].guest },
					},
					secondary: {
						service: toAppointmentService(entries[1].service),
						guest: { ...entries[1].guest },
					},
					slot,
				});

				entries.forEach(({ guest }, index) => {
					guest.date = slot.date;
					guest.slot = result.slotsByGuestKey[guest.guestKey];
					const appointment =
						index === 0 ? result.primaryAppointment : result.secondaryAppointment;
					guest.appointmentId =
						appointment?.name || appointment?.appointmentId || guest.appointmentId;
					syncGuestCompletion(guest);
				});
				this.coupleSelectedDate = slot.date;
			} catch (error) {
				const message =
					error?.message || "Both appointments could not be reserved together.";
				this.coupleError = message;
				this.errorByGuest = {
					...this.errorByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, message])),
				};
			} finally {
				this.isReservingSlots = {
					...this.isReservingSlots,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, false])),
				};
				this.reservingSlotIdByGuest = {
					...this.reservingSlotIdByGuest,
					...Object.fromEntries(guestKeys.map((guestKey) => [guestKey, ""])),
				};
			}
		},
		async updateGuestNotes(serviceKey, guestKey, notes) {
			const workflowStore = useBookingWorkflowStore();
			const serviceIndex = findServiceIndex(this.assignments, serviceKey);
			if (serviceIndex === -1) return;
			const service = this.assignments[serviceIndex];
			const guestIndex = findGuestIndex(service, guestKey);
			if (guestIndex === -1) return;

			const guest = service.guests[guestIndex];
			guest.notes = notes || "";
			this.errorByGuest = { ...this.errorByGuest, [guestKey]: "" };

			try {
				await workflowStore.updateAppointmentNotes({
					guestKey,
					appointmentId: guest.appointmentId,
					notes: guest.notes,
				});
			} catch (error) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]: error?.message || "Appointment notes could not be saved.",
				};
			}
		},
	},
});
