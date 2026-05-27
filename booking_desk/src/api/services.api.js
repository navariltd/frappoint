import { createResource } from "frappe-ui";
import { fetchBookingDeskCacheVersion } from "@/api/cacheVersion.api";
import { CACHE_MAX_AGE, CACHE_TAGS, getMemoryCache, setMemoryCache } from "@/utils/cachePolicy";

const SERVICE_TYPE_ENDPOINT = "frappoint.frappoint.api.service_type.get_service_types";
const SERVICE_TYPE_DETAILS_ENDPOINT =
	"frappoint.frappoint.api.service_type.get_service_type_details";
const CUSTOMER_DOCTYPE = "Customer";
const APPOINTMENT_DOCTYPE = "Service Appointment";

const serviceTypesResource = createResource({
	url: SERVICE_TYPE_ENDPOINT,
	method: "GET",
	auto: false,
});

const serviceTypeDetailsResource = createResource({
	url: SERVICE_TYPE_DETAILS_ENDPOINT,
	method: "GET",
	auto: false,
});

const customerSearchResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

const customerAppointmentsResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

const unwrapListPayload = (payload) => {
	if (Array.isArray(payload)) {
		return payload;
	}
	if (Array.isArray(payload?.message)) {
		return payload.message;
	}
	return [];
};

const SERVICE_TYPES_CACHE_KEY = "reference:service-types";

export async function fetchServiceTypes() {
	const versions = await fetchBookingDeskCacheVersion();
	const cached = getMemoryCache(SERVICE_TYPES_CACHE_KEY, {
		version: versions.serviceTypesVersion,
	});

	if (cached) {
		return cached;
	}

	const response = await serviceTypesResource.fetch({
		active_only: true,
		page: 1,
		page_size: 500,
	});

	const payload = response ?? serviceTypesResource.data;
	if (Array.isArray(payload?.data)) {
		return setMemoryCache(SERVICE_TYPES_CACHE_KEY, payload.data, {
			maxAge: CACHE_MAX_AGE.MEDIUM,
			tags: [CACHE_TAGS.SERVICES],
			version: versions.serviceTypesVersion,
		});
	}
	if (Array.isArray(payload?.message?.data)) {
		return setMemoryCache(SERVICE_TYPES_CACHE_KEY, payload.message.data, {
			maxAge: CACHE_MAX_AGE.MEDIUM,
			tags: [CACHE_TAGS.SERVICES],
			version: versions.serviceTypesVersion,
		});
	}
	return [];
}

export async function fetchServiceTypeDetails(serviceType) {
	if (!serviceType) {
		return null;
	}

	const response = await serviceTypeDetailsResource.fetch({
		service_type: serviceType,
	});

	const payload = response ?? serviceTypeDetailsResource.data;
	if (payload?.message) {
		return payload.message;
	}
	return payload ?? null;
}

export async function fetchCustomers(pageLength = 100) {
	return searchCustomers("", pageLength);
}

export async function searchCustomers(query = "", pageLength = 50) {
	const term = String(query || "").trim();
	const normalizedPageLength = Math.max(1, Math.min(Number(pageLength) || 50, 100));
	const orFilters = [];

	if (term) {
		const needle = `%${term}%`;
		orFilters.push(["name", "like", needle], ["customer_name", "like", needle]);
	}

	const response = await customerSearchResource.fetch({
		doctype: CUSTOMER_DOCTYPE,
		fields: ["name", "customer_name"],
		or_filters: orFilters.length ? orFilters : undefined,
		order_by: "customer_name asc",
		limit_start: 0,
		limit_page_length: normalizedPageLength,
	});

	return unwrapListPayload(response ?? customerSearchResource.data);
}

export async function fetchCustomerRecentAppointments(customerId) {
	if (!customerId) {
		return [];
	}

	const response = await customerAppointmentsResource.fetch({
		doctype: APPOINTMENT_DOCTYPE,
		fields: [
			"name",
			"customer",
			"full_name",
			"email",
			"mobile_no",
			"appointment_date",
			"outstanding_amount",
			"status",
		],
		filters: [["customer", "=", customerId]],
		order_by: "appointment_date desc, modified desc",
		limit_page_length: 30,
	});

	return unwrapListPayload(response ?? customerAppointmentsResource.data);
}

export {
	SERVICE_TYPE_ENDPOINT,
	SERVICE_TYPE_DETAILS_ENDPOINT,
	CUSTOMER_DOCTYPE,
	APPOINTMENT_DOCTYPE,
	serviceTypesResource,
	serviceTypeDetailsResource,
	customerSearchResource,
	customerAppointmentsResource,
};
