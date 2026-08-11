import { defineStore } from "pinia";
import { createEmptyAppointmentDetails } from "@/types/appointment-details";
import { useAppointmentEventLogsStore } from "@/stores/appointmentEventLogs.store";
import {
	fetchAppointmentAvailability,
	fetchAppointmentDetails,
	performAppointmentAction,
} from "@/services/appointmentDetails.service";
import { CACHE_TAGS, invalidateMemoryCacheByTag } from "@/utils/cachePolicy";

const createEmptyBookingContext = () => ({
	bookingId: "",
	status: "Draft",
	customerName: "",
	email: "",
	mobileNo: "",
	currency: "KES",
	bookingDate: "",
	appointmentCount: 0,
	totalGuests: 0,
	grandTotal: 0,
	outstandingAmount: 0,
	appointments: [],
	items: [],
});

const getErrorMessage = (error, fallback) => {
	if (Array.isArray(error?.messages) && error.messages.length) {
		return error.messages.join(" ");
	}

	if (error?._server_messages) {
		try {
			const serverMessages = JSON.parse(error._server_messages);
			const messages = serverMessages
				.map((message) => {
					try {
						return JSON.parse(message)?.message || message;
					} catch {
						return message;
					}
				})
				.filter(Boolean);
			if (messages.length) {
				return messages.join(" ");
			}
		} catch {
			return String(error._server_messages);
		}
	}

	return error?.message || fallback;
};

export const useAppointmentDetailsStore = defineStore("appointmentDetails", {
	state: () => ({
		appointment: createEmptyAppointmentDetails(),
		booking: createEmptyBookingContext(),
		payments: [],
		timeline: [],
		alerts: [],
		availabilityDates: [],
		availabilitySlots: [],
		selectedAvailabilityDate: "",
		selectedAvailabilitySlotId: "",
		paymentSummary: null,
		actionState: {},
		isLoading: false,
		isLoadingAvailability: false,
		isSubmittingAction: false,
		error: "",
	}),
	getters: {
		hasAppointment(state) {
			return Boolean(state.appointment?.appointmentId);
		},
		hasBookingContext(state) {
			return Boolean(state.booking?.bookingId);
		},
		financialSummary(state) {
			const totalAmount = Number(state.appointment.totalAmount || 0);
			const discountAmount = Number(
				state.paymentSummary?.discountAmount ?? state.appointment.discountAmount ?? 0
			);
			const finalAmount = Number(
				state.paymentSummary?.finalAmount ?? Math.max(0, totalAmount - discountAmount)
			);
			const paidAmount = Number(state.paymentSummary?.paidAmount || 0);
			const outstandingAmount = Number(
				state.paymentSummary?.outstandingAmount ?? state.appointment.outstandingAmount ?? 0
			);
			return {
				currency: state.paymentSummary?.currency || state.appointment.currency || "KES",
				totalAmount,
				discountAmount,
				finalAmount,
				paidAmount,
				outstandingAmount,
				balance: outstandingAmount,
			};
		},
		summaryMetrics(state) {
			return {
				appointmentId: state.appointment.appointmentId,
				bookingId: state.appointment.bookingId,
				status: state.appointment.status || "Open",
				paymentStatus: state.appointment.paymentStatus || "Unpaid",
				provider: state.appointment.provider || "Unassigned",
				appointmentDate: state.appointment.appointmentDate || "",
			};
		},
	},
	actions: {
		setSelectedAvailabilityDate(date) {
			this.selectedAvailabilityDate = date || "";
		},
		setSelectedAvailabilitySlot(slot) {
			this.selectedAvailabilitySlotId = slot?.id || "";
			this.selectedAvailabilityDate = slot?.date || this.selectedAvailabilityDate;
		},
		async fetchAppointment(appointmentId) {
			const eventLogsStore = useAppointmentEventLogsStore();
			if (!appointmentId) {
				this.error = "Appointment ID is required.";
				eventLogsStore.reset();
				return;
			}
			this.isLoading = true;
			this.error = "";
			try {
				const payload = await fetchAppointmentDetails(appointmentId);
				this.appointment = payload.appointment || createEmptyAppointmentDetails();
				this.booking = payload.booking || createEmptyBookingContext();
				this.payments = payload.payments || [];
				this.timeline = payload.timeline || [];
				this.alerts = payload.alerts || [];
				this.paymentSummary = payload.paymentSummary || null;
				this.actionState = payload.actions || {};
				eventLogsStore.hydrateFromPayload(
					payload.eventLogs || [],
					payload.timeTracking || {}
				);
				this.selectedAvailabilityDate =
					payload.availability?.date || this.appointment.appointmentDate;
				this.selectedAvailabilitySlotId = "";
				await this.refreshAvailability();
			} catch (error) {
				this.error = error?.message || "Could not load appointment details.";
			} finally {
				this.isLoading = false;
			}
		},
		async refreshAvailability() {
			const serviceType = this.appointment.appointmentType;
			const duration = Number(this.appointment.duration || 0);
			const provider = this.appointment.providerId || this.appointment.provider || "";
			const date = this.selectedAvailabilityDate || this.appointment.appointmentDate;
			if (!serviceType || !date) {
				this.availabilityDates = [];
				this.availabilitySlots = [];
				return;
			}

			this.isLoadingAvailability = true;
			try {
				const availability = await fetchAppointmentAvailability({
					serviceType,
					duration,
					provider,
					date,
				});
				this.availabilityDates = availability.dates || [];
				this.availabilitySlots = availability.slots || [];
				if (
					!this.availabilitySlots.find(
						(slot) => slot.id === this.selectedAvailabilitySlotId
					) &&
					this.availabilitySlots.length
				) {
					this.selectedAvailabilitySlotId = this.availabilitySlots[0].id;
				}
			} finally {
				this.isLoadingAvailability = false;
			}
		},
		async performAction(payload) {
			const eventLogsStore = useAppointmentEventLogsStore();
			const actionPayload = {
				appointmentId: payload.appointmentId || this.appointment.appointmentId,
				action: payload.action,
				newAppointmentDate: payload.newAppointmentDate,
				newStartTime: payload.newStartTime,
				newEndTime: payload.newEndTime,
				newProvider: payload.newProvider,
				newSlotIds: payload.newSlotIds,
				newServiceUnit: payload.newServiceUnit,
				actualStartTime: payload.actualStartTime,
				actualEndTime: payload.actualEndTime,
				cancellationReasons: payload.cancellationReasons,
			};

			this.isSubmittingAction = true;
			this.error = "";
			try {
				const response = await performAppointmentAction(actionPayload);
				const nextAppointmentId =
					response?.appointment?.appointmentId ||
					response?.appointment?.name ||
					actionPayload.appointmentId;
				if (response?.appointment) {
					this.appointment = response.appointment;
				}
				if (response?.booking) {
					this.booking = response.booking;
				}
				if (response?.payments) {
					this.payments = response.payments;
				}
				if (response?.timeline) {
					this.timeline = response.timeline;
				}
				if (response?.alerts) {
					this.alerts = response.alerts;
				}
				this.paymentSummary = response?.paymentSummary || this.paymentSummary;
				this.actionState = response?.actions || this.actionState;
				invalidateMemoryCacheByTag(CACHE_TAGS.DASHBOARD);
				invalidateMemoryCacheByTag(CACHE_TAGS.BOOKINGS);
				eventLogsStore.hydrateFromPayload(
					response?.eventLogs || [],
					response?.timeTracking || {}
				);
				this.selectedAvailabilityDate =
					response?.availability?.date || this.selectedAvailabilityDate;
				this.selectedAvailabilitySlotId = "";
				if (["edit_time_slot", "reschedule"].includes(actionPayload.action)) {
					await this.refreshAvailability();
				}
				return {
					...response,
					nextAppointmentId,
				};
			} catch (error) {
				this.error = getErrorMessage(error, "Could not complete the appointment action.");
				throw error;
			} finally {
				this.isSubmittingAction = false;
			}
		},
		async retry(appointmentId) {
			await this.fetchAppointment(appointmentId || this.appointment.appointmentId);
		},
	},
});
