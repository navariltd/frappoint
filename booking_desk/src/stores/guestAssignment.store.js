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
	}),
	getters: {
		progress(state) {
			return getAssignmentProgress(state.assignments);
		},
		validationIssues(state) {
			return buildValidationIssues(state.assignments);
		},
		isComplete() {
			return this.validationIssues.length === 0 && this.progress.totalGuests > 0;
		},
		summaryRows(state) {
			return summarizeAssignments(state.assignments);
		},
	},
	actions: {
		initialize({
			cartItems = [],
			customers = [],
			selectedCustomerId = "",
			selectedCustomer = null,
			appointmentsByGuestKey = {},
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
			this.activeServiceIndex = 0;
			this.activeGuestIndex = 0;
			this.isLoadingDates = {};
			this.isLoadingSlots = {};
			this.isReservingSlots = {};
			this.reservingSlotIdByGuest = {};
			this.errorByGuest = {};
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
			guest.date = "";
			guest.slot = null;
			guest.availableDates = [];
			guest.availableSlots = [];
			syncGuestCompletion(guest);

			if (guest.fullName) {
				await this.fetchGuestDates(serviceKey, guestKey);
			}
		},
	},
});
