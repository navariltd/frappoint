import { createListResource, createResource } from "frappe-ui";

const PROVIDER_DOCTYPE = "Service Provider";

const providersListResource = createListResource({
	doctype: PROVIDER_DOCTYPE,
	fields: [
		"name",
		"provider_name",
		"first_name",
		"last_name",
		"designation",
		"active",
		"color_code",
	],
	filters: { active: 1 },
	orderBy: "provider_name asc",
	pageLength: 500,
	auto: false,
	cache: ["dashboard", "providers"],
});

const providerLookupResource = createResource({
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

export async function fetchProviders() {
	await providersListResource.fetch();
	return unwrapListPayload(providersListResource.data);
}

export async function fetchProvidersByIds(providerIds = []) {
	const ids = Array.from(
		new Set(providerIds.map((id) => String(id || "").trim()).filter(Boolean))
	);

	if (!ids.length) {
		return [];
	}

	const response = await providerLookupResource.fetch({
		doctype: PROVIDER_DOCTYPE,
		fields: ["name", "provider_name", "first_name", "last_name", "designation", "active"],
		filters: [["name", "in", ids]],
		order_by: "provider_name asc",
		limit_page_length: ids.length,
	});

	return unwrapListPayload(response ?? providerLookupResource.data);
}

export { providersListResource, providerLookupResource, PROVIDER_DOCTYPE };
