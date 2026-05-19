import { createResource } from "frappe-ui";

const GET_SERVICE_BOOKINGS_WORKSPACE_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_service_bookings_workspace";

const bookingsWorkspaceResource = createResource({
	url: GET_SERVICE_BOOKINGS_WORKSPACE_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

export async function fetchBookingsWorkspaceApi(params = {}) {
	const response = await bookingsWorkspaceResource.fetch({
		search_text: params.searchText || "",
		customer_query: params.customerQuery || "",
		statuses: JSON.stringify(params.statuses || []),
		payment_statuses: JSON.stringify(params.paymentStatuses || []),
		from_date: params.fromDate || "",
		to_date: params.toDate || "",
		page: params.page || 1,
		page_size: params.pageSize || 20,
	});

	return unwrapPayload(response ?? bookingsWorkspaceResource.data);
}
