import { createResource } from "frappe-ui";

const appointmentsListResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

function asArray(value) {
	return Array.isArray(value) ? value : [];
}

function buildFilters(params = {}) {
	const filters = [["docstatus", "!=", 2]];

	if (params.statuses?.length) {
		filters.push(["status", "in", params.statuses]);
	}

	if (params.paymentStatuses?.length) {
		filters.push(["payment_status", "in", params.paymentStatuses]);
	}

	if (params.provider) {
		filters.push(["appointment_provider", "=", params.provider]);
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

function buildOrFilters(params = {}) {
	const orFilters = [];
	const searchText = String(params.searchText || "").trim();
	const customerQuery = String(params.customerQuery || "").trim();
	const bookingReference = String(params.bookingReference || "").trim();

	if (searchText) {
		const needle = `%${searchText}%`;
		orFilters.push(
			["name", "like", needle],
			["booking_id", "like", needle],
			["full_name", "like", needle],
			["customer", "like", needle],
			["appointment_type", "like", needle],
			["service_provider_name", "like", needle],
			["appointment_provider", "like", needle],
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

	if (bookingReference) {
		orFilters.push(["booking_id", "like", `%${bookingReference}%`]);
	}

	return orFilters;
}

function normalizeAppointment(row) {
	const durationMinutes = Number(row.duration || 0);
	return {
		id: row.name,
		appointmentId: row.name,
		bookingId: row.booking_id || "",
		customerName: row.full_name || row.customer || "Walk-in Customer",
		customer: row.customer || "",
		provider: row.service_provider_name || row.appointment_provider || "Unassigned",
		providerId: row.appointment_provider || "",
		service: row.appointment_type || "Service",
		appointmentDate: row.appointment_date || "",
		startTime: row.start_time || "",
		endTime: row.end_time || "",
		duration: durationMinutes,
		status: row.status || "Open",
		paymentStatus: row.payment_status || "Unpaid",
		currency: row.currency || "KES",
		totalAmount: Number(row.total_amount || 0),
		outstandingAmount: Number(row.outstanding_amount || 0),
		details: row.details || "",
		mobileNo: row.mobile_no || "",
		email: row.email || "",
		modified: row.modified || "",
		coupleAppointmentId: row.couple_appointment_id || "",
		isPrimaryInCouple: Boolean(row.is_primary_in_couple),
		isCouple: Boolean(row.couple_appointment_id),
	};
}

function summarizeMetrics(appointments) {
	const total = appointments.length;
	const inProgress = appointments.filter((item) => item.status === "In Progress").length;
	const checkedIn = appointments.filter((item) => item.status === "Checked In").length;
	const completed = appointments.filter((item) => item.status === "Completed").length;
	const pendingPayment = appointments.filter((item) => item.outstandingAmount > 0).length;
	const delayed = appointments.filter((item) => item.status === "Rescheduled").length;

	return {
		total,
		inProgress,
		checkedIn,
		completed,
		pendingPayment,
		delayed,
	};
}

function uniqueSorted(values) {
	return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
		String(a).localeCompare(String(b))
	);
}

export async function fetchAppointmentsWorkspace(params = {}) {
	const page = Math.max(Number(params.page || 1), 1);
	const pageSize = Math.max(Number(params.pageSize || 24), 1);

	const response = await appointmentsListResource.fetch({
		doctype: "Service Appointment",
		fields: [
			"name",
			"booking_id",
			"customer",
			"full_name",
			"mobile_no",
			"email",
			"appointment_type",
			"appointment_provider",
			"service_provider_name",
			"appointment_date",
			"start_time",
			"end_time",
			"duration",
			"status",
			"payment_status",
			"currency",
			"total_amount",
			"outstanding_amount",
			"details",
			"couple_appointment_id",
			"is_primary_in_couple",
			"modified",
		],
		filters: buildFilters(params),
		or_filters: buildOrFilters(params).length ? buildOrFilters(params) : undefined,
		order_by: "appointment_date desc, start_time asc, modified desc",
		limit_start: (page - 1) * pageSize,
		limit_page_length: pageSize + 1,
	});

	const rows = asArray(response?.message || response || appointmentsListResource.data || []);
	const hasMore = rows.length > pageSize;
	const normalizedAppointments = rows.slice(0, pageSize).map(normalizeAppointment);

	return {
		appointments: normalizedAppointments,
		page,
		pageSize,
		hasMore,
	};
}

export async function fetchAppointmentMetrics(params = {}) {
	const response = await appointmentsListResource.fetch({
		doctype: "Service Appointment",
		fields: [
			"name",
			"status",
			"outstanding_amount",
			"appointment_provider",
			"service_provider_name",
		],
		filters: buildFilters(params),
		or_filters: buildOrFilters(params).length ? buildOrFilters(params) : undefined,
		order_by: "modified desc",
		limit_start: 0,
		limit_page_length: 500,
	});

	const rows = asArray(response?.message || response || appointmentsListResource.data || []).map(
		normalizeAppointment
	);

	return {
		metrics: summarizeMetrics(rows),
		providerOptions: uniqueSorted(rows.map((item) => item.provider)),
		statusOptions: uniqueSorted(rows.map((item) => item.status)),
		paymentStatusOptions: uniqueSorted(rows.map((item) => item.paymentStatus)),
	};
}
