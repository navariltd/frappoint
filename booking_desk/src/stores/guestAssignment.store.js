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
	validateSlotAvailability,
} from "@/services/availability.service";
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
		errorByGuest: {},
		customers: [],
		selectedCustomerId: "",
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
			appointmentsByGuestKey = {},
		}) {
			this.customers = customers;
			this.selectedCustomerId = selectedCustomerId;
			const selectedCustomer =
				customers.find((item) => item.id === selectedCustomerId) || null;
			this.assignments = buildAssignmentsFromCart(
				cartItems,
				selectedCustomer,
				appointmentsByGuestKey
			);
			this.activeServiceIndex = 0;
			this.activeGuestIndex = 0;
			this.isLoadingDates = {};
			this.isLoadingSlots = {};
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
				date: "",
				slot: null,
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
				const dates = await fetchNormalizedAvailableDates({
					serviceType: service.serviceId,
					duration: service.duration,
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

			const validation = await validateSlotAvailability(slot.slotIds || []);
			if (!validation.available) {
				this.errorByGuest = {
					...this.errorByGuest,
					[guestKey]:
						"Selected slot is no longer available. Please choose another slot.",
				};
				return;
			}

			this.isLoadingSlots = { ...this.isLoadingSlots, [guestKey]: true };
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
				this.isLoadingSlots = { ...this.isLoadingSlots, [guestKey]: false };
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
	},
});
