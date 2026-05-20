import { createResource } from "frappe-ui";

export async function fetchServiceDetails(serviceType) {
	const resource = createResource({
		url: "frappoint.frappoint.api.service_type.get_service_type_details",
		method: "GET",
		makeParams: () => ({
			service_type: serviceType,
		}),
	});

	return resource.fetch();
}
