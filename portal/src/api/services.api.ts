import { createResource } from "frappe-ui";

export async function fetchServiceTypes(params = {}) {
	const resource = createResource({
		url: "frappoint.frappoint.api.service_type.get_service_types",
		makeParams() {
			return params;
		},
	});

	const response = await resource.fetch();
	return response || { data: [], pagination: null };
}

export async function fetchServicePriceRange(params = {}) {
	const resource = createResource({
		url: "frappoint.frappoint.api.service_type.get_price_range",
		makeParams() {
			return params;
		},
	});

	const response = await resource.fetch();
	return response || { min_price: 0, max_price: 500, currency: "USD" };
}
