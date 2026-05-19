import {
	fetchNormalizedAvailableDates,
	fetchNormalizedAvailableSlots,
} from "@/services/availability.service";
import {
	fetchAppointmentDetailsApi,
	performAppointmentActionApi,
} from "@/api/appointmentDetails.api";
import { createEmptyAppointmentDetails } from "@/types/appointment-details";

const toNumber = (value) => Number(value || 0);

function normalizeBooking(raw = {}) {
	return {
		name: raw.name || raw.bookingId || "",
		bookingId: raw.name || raw.bookingId || "",
		status: raw.status || "Draft",
		customer: raw.customer || "",
		customerName: raw.fullName || raw.customerName || "Walk-in Customer",
		email: raw.email || "",
		mobileNo: raw.mobileNo || "",
		currency: raw.currency || "KES",
		bookingDate: raw.bookingDate || "",
		appointmentCount: Number(raw.appointmentCount || (raw.appointments || []).length),
		totalGuests: Number(raw.totalGuests || 0),
		subtotal: toNumber(raw.subtotal),
		grandTotal: toNumber(raw.grandTotal),
		paidAmount: toNumber(raw.paidAmount),
		outstandingAmount: toNumber(raw.outstandingAmount),
		appointments: Array.isArray(raw.appointments)
			? raw.appointments.map((appointment) => ({
					id: appointment.name || appointment.appointmentId || "",
					appointmentId: appointment.name || appointment.appointmentId || "",
					serviceType:
						appointment.serviceType || appointment.appointmentType || "Service",
					provider: appointment.provider || "Unassigned",
					date: appointment.date || appointment.appointmentDate || "",
					startTime: appointment.startTime || "",
					endTime: appointment.endTime || "",
					status: appointment.status || "Open",
					paymentStatus: appointment.paymentStatus || "Unpaid",
			  }))
			: [],
		items: Array.isArray(raw.items) ? raw.items : [],
	};
}

function normalizePayment(payment = {}) {
	return {
		id: payment.name || payment.id || "",
		name: payment.name || payment.id || "",
		referenceDocname: payment.referenceDocname || payment.reference_docname || "",
		modeOfPayment: payment.modeOfPayment || payment.mode_of_payment || "",
		paymentGateway: payment.paymentGateway || payment.payment_gateway || "",
		postingDate: payment.postingDate || payment.posting_date || "",
		referenceDate: payment.referenceDate || payment.reference_date || "",
		paymentReceived: Boolean(payment.paymentReceived ?? payment.payment_received),
		currency: payment.currency || "KES",
		amount: toNumber(payment.amount),
		paymentId: payment.paymentId || payment.payment_id || "",
		orderId: payment.orderId || payment.order_id || "",
	};
}

function normalizeTimelineItem(item = {}) {
	return {
		id: item.id || item.name || `${item.label || "event"}-${item.timestamp || ""}`,
		label: item.label || "Update",
		detail: item.detail || "",
		tone: item.tone || "neutral",
		timestamp: item.timestamp || "",
	};
}

function normalizeAlert(alert = {}) {
	return {
		id: alert.id || alert.label || "alert",
		severity: alert.severity || "info",
		label: alert.label || "Notice",
		message: alert.message || "",
	};
}

function normalizeAppointment(raw = {}) {
	const appointment = createEmptyAppointmentDetails();

	return {
		...appointment,
		name: raw.name || raw.appointmentId || appointment.name,
		appointmentId: raw.appointmentId || raw.name || appointment.appointmentId,
		bookingId: raw.bookingId || appointment.bookingId,
		status: raw.status || appointment.status,
		paymentStatus: raw.paymentStatus || appointment.paymentStatus,
		customer: raw.customer || raw.customerName || appointment.customer,
		customerName: raw.customerName || raw.fullName || raw.customer || appointment.customerName,
		fullName: raw.fullName || raw.customerName || raw.customer || appointment.fullName,
		email: raw.email || appointment.email,
		mobileNo: raw.mobileNo || appointment.mobileNo,
		currency: raw.currency || appointment.currency,
		appointmentType: raw.appointmentType || appointment.appointmentType,
		appointmentDate: raw.appointmentDate || appointment.appointmentDate,
		startTime: raw.startTime || appointment.startTime,
		endTime: raw.endTime || appointment.endTime,
		actualStartTime: raw.actualStartTime || appointment.actualStartTime,
		actualEndTime: raw.actualEndTime || appointment.actualEndTime,
		duration: Number(raw.duration || appointment.duration),
		serviceUnit: raw.serviceUnit || appointment.serviceUnit,
		provider: raw.provider || appointment.provider,
		serviceProviderName: raw.serviceProviderName || appointment.serviceProviderName,
		appointmentPrice: raw.appointmentPrice || appointment.appointmentPrice,
		totalAmount: toNumber(raw.totalAmount),
		grandTotal: toNumber(raw.grandTotal || raw.totalAmount),
		outstandingAmount: toNumber(raw.outstandingAmount),
		details: raw.details || appointment.details,
		notes: raw.notes || appointment.notes,
		source: raw.source || appointment.source,
		selectedSlotIds: Array.isArray(raw.selectedSlotIds) ? raw.selectedSlotIds : [],
		allAvailableProviders: Array.isArray(raw.allAvailableProviders)
			? raw.allAvailableProviders
			: [],
		modified: raw.modified || appointment.modified,
		creation: raw.creation || appointment.creation,
	};
}

export async function fetchAppointmentDetails(appointmentId) {
	const payload = (await fetchAppointmentDetailsApi(appointmentId)) || {};
	const appointment = normalizeAppointment(payload.appointment || payload);
	const booking = payload.booking ? normalizeBooking(payload.booking) : null;
	const payments = Array.isArray(payload.payments) ? payload.payments.map(normalizePayment) : [];
	const timeline = Array.isArray(payload.timeline)
		? payload.timeline.map(normalizeTimelineItem)
		: [];
	const alerts = Array.isArray(payload.alerts) ? payload.alerts.map(normalizeAlert) : [];

	return {
		appointment,
		booking,
		payments,
		timeline,
		alerts,
		paymentSummary: {
			currency: payload.paymentSummary?.currency || appointment.currency,
			totalAmount: toNumber(payload.paymentSummary?.totalAmount || appointment.totalAmount),
			paidAmount: toNumber(payload.paymentSummary?.paidAmount),
			outstandingAmount: toNumber(
				payload.paymentSummary?.outstandingAmount || appointment.outstandingAmount
			),
		},
		actions: payload.actions || {},
		availability: payload.availability || {
			serviceType: appointment.appointmentType,
			duration: appointment.duration,
			provider: appointment.provider,
			date: appointment.appointmentDate,
		},
	};
}

export async function fetchAppointmentAvailability({ serviceType, duration, provider, date }) {
	if (!serviceType || !date) {
		return { dates: [], slots: [] };
	}

	const [dates, slots] = await Promise.all([
		fetchNormalizedAvailableDates({ serviceType, duration, provider }),
		fetchNormalizedAvailableSlots({ serviceType, duration, provider, date }),
	]);

	return { dates, slots };
}

export async function performAppointmentAction(payload) {
	return performAppointmentActionApi(payload);
}
