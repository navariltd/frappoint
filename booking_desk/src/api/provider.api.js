import { createResource } from "frappe-ui";
import { fetchBookingDeskCacheVersion } from "@/api/cacheVersion.api";
import { CACHE_MAX_AGE, CACHE_TAGS, getMemoryCache, setMemoryCache } from "@/utils/cachePolicy";

const PROVIDER_DOCTYPE = "Service Provider";

const providersListResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
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

const PROVIDERS_CACHE_KEY = "reference:providers";
const GENDERS_CACHE_KEY = "reference:genders";

export async function fetchProviders() {
	const versions = await fetchBookingDeskCacheVersion();
	const cached = getMemoryCache(PROVIDERS_CACHE_KEY, {
		version: versions.providersVersion,
	});

	if (cached) {
		return cached;
	}

	const response = await providersListResource.fetch({
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
		order_by: "provider_name asc",
		limit_page_length: 500,
	});

	const rows = unwrapListPayload(response ?? providersListResource.data);
	return setMemoryCache(PROVIDERS_CACHE_KEY, rows, {
		maxAge: 2 * 60 * 1000,
		tags: [CACHE_TAGS.PROVIDERS],
		version: versions.providersVersion,
	});
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

const genderResource = createResource({
	url: "frappe.client.get_list",
	auto: false,
});

export async function fetchAvailableGenders() {
	const cached = getMemoryCache(GENDERS_CACHE_KEY);
	if (cached) {
		return cached;
	}

	const response = await genderResource.fetch({
		doctype: "Gender",
		fields: ["name"],
		order_by: "name asc",
		limit_page_length: 100,
	});

	const genders = unwrapListPayload(response ?? genderResource.data).map((g) => ({
		name: g.name,
		label: g.name,
	}));

	return setMemoryCache(GENDERS_CACHE_KEY, genders, {
		maxAge: CACHE_MAX_AGE.MEDIUM,
		tags: [CACHE_TAGS.PROVIDERS],
	});
}

export { providersListResource, providerLookupResource, genderResource, PROVIDER_DOCTYPE };
