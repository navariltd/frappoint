import { createResource } from "frappe-ui";
import { performAppointmentAction } from "@/services/appointmentDetails.service";

const calendarAppointmentsResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

function asArray(value) {
	return Array.isArray(value) ? value : [];
}

function uniqueSorted(values) {
	return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
		String(a).localeCompare(String(b))
	);
}

function parseDateTime(dateValue, timeValue) {
	if (!dateValue || !timeValue) {
		return null;
	}
	const asDate = new Date(`${dateValue}T${timeValue}`);
	return Number.isNaN(asDate.getTime()) ? null : asDate;
}

function addMinutes(dateObj, minutes) {
	if (!dateObj || Number.isNaN(minutes)) {
		return null;
	}
	return new Date(dateObj.getTime() + minutes * 60000);
}

function createFilters(params = {}) {
	const filters = [["docstatus", "!=", 2]];

	if (params.statuses?.length) {
		filters.push(["status", "in", params.statuses]);
	}
	if (params.provider) {
		filters.push(["appointment_provider", "=", params.provider]);
	}
	if (params.resource) {
		filters.push(["service_unit", "=", params.resource]);
	}
	if (params.fromDate && params.toDate) {
		filters.push(["appointment_date", "between", [params.fromDate, params.toDate]]);
	} else if (params.fromDate) {
		filters.push(["appointment_date", ">=", params.fromDate]);
	} else if (params.toDate) {
		filters.push(["appointment_date", "<=", params.toDate]);
	}

	return filters;
}

function createOrFilters(params = {}) {
	const searchText = String(params.searchText || "").trim();
	const customerQuery = String(params.customerQuery || "").trim();
	const orFilters = [];

	if (searchText) {
		const needle = `%${searchText}%`;
		orFilters.push(
			["name", "like", needle],
			["booking_id", "like", needle],
			["full_name", "like", needle],
			["customer", "like", needle],
			["appointment_type", "like", needle],
			["service_provider_name", "like", needle],
			["mobile_no", "like", needle]
		);
	}

	if (customerQuery) {
		const needle = `%${customerQuery}%`;
		orFilters.push(
			["full_name", "like", needle],
			["customer", "like", needle],
			["mobile_no", "like", needle]
		);
	}

	return orFilters;
}

function normalizeEvent(row = {}) {
	const startAt = parseDateTime(row.appointment_date, row.start_time);
	const duration = Number(row.duration || 0);
	const computedEnd = addMinutes(startAt, duration || 60);
	const endAt = parseDateTime(row.appointment_date, row.end_time) || computedEnd || startAt;

	return {
		id: row.name,
		appointmentId: row.name,
		bookingId: row.booking_id || "",
		customerName: row.full_name || row.customer || "Walk-in Customer",
		provider: row.service_provider_name || row.appointment_provider || "Unassigned",
		providerId: row.appointment_provider || "",
		resource: row.service_unit || "",
		service: row.appointment_type || "Service",
		status: row.status || "Open",
		paymentStatus: row.payment_status || "Unpaid",
		date: row.appointment_date || "",
		startTime: row.start_time || "",
		endTime: row.end_time || "",
		duration: duration || 60,
		startAt,
		endAt,
		details: row.details || "",
		mobileNo: row.mobile_no || "",
		email: row.email || "",
	};
}

async function fetchRawRows(params = {}) {
	const basePayload = {
		doctype: "Service Appointment",
		order_by: "appointment_date asc, start_time asc, modified desc",
		filters: createFilters(params),
		or_filters: createOrFilters(params).length ? createOrFilters(params) : undefined,
		limit_start: 0,
		limit_page_length: Math.max(Number(params.pageSize || 500), 100),
	};

	const extendedFields = [
		"name",
		"booking_id",
		"customer",
		"full_name",
		"mobile_no",
		"email",
		"appointment_type",
		"appointment_provider",
		"service_provider_name",
		"service_unit",
		"appointment_date",
		"start_time",
		"end_time",
		"duration",
		"status",
		"payment_status",
		"details",
		"modified",
	];

	try {
		const response = await calendarAppointmentsResource.fetch({
			...basePayload,
			fields: extendedFields,
		});
		return asArray(response?.message || response || calendarAppointmentsResource.data || []);
	} catch (error) {
		// Fallback for sites where service_unit custom field is unavailable.
		const fallbackResponse = await calendarAppointmentsResource.fetch({
			...basePayload,
			fields: extendedFields.filter((field) => field !== "service_unit"),
		});
		return asArray(
			fallbackResponse?.message ||
				fallbackResponse ||
				calendarAppointmentsResource.data ||
				[]
		);
	}
}

export async function fetchCalendarEvents(params = {}) {
	const rows = await fetchRawRows(params);
	const events = rows.map(normalizeEvent).filter((row) => row.startAt);

	return {
		events,
		providerOptions: uniqueSorted(events.map((event) => event.provider)),
		resourceOptions: uniqueSorted(events.map((event) => event.resource)),
		statusOptions: uniqueSorted(events.map((event) => event.status)),
	};
}

export async function runCalendarAppointmentAction({ appointmentId, action }) {
	if (!appointmentId || !action) {
		return null;
	}
	return performAppointmentAction({ appointmentId, action });
}
