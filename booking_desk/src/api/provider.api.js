import { createListResource } from "frappe-ui";

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

export { providersListResource, PROVIDER_DOCTYPE };
