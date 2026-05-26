import { createResource } from "frappe-ui";
import { CACHE_MAX_AGE, CACHE_TAGS, getMemoryCache, setMemoryCache } from "@/utils/cachePolicy";

const CACHE_VERSION_ENDPOINT =
	"frappoint.frappoint.api.booking_desk.get_booking_desk_cache_version";
const CACHE_KEY = "reference:cache-version";

const cacheVersionResource = createResource({
	url: CACHE_VERSION_ENDPOINT,
	auto: false,
});

const unwrapPayload = (payload) => payload?.message ?? payload ?? {};

const normalizeVersionPayload = (payload) => ({
	serviceTypesVersion: String(payload?.serviceTypesVersion || ""),
	providersVersion: String(payload?.providersVersion || ""),
	customersVersion: String(payload?.customersVersion || ""),
	bookingsVersion: String(payload?.bookingsVersion || ""),
	generatedAt: String(payload?.generatedAt || ""),
});

export async function fetchBookingDeskCacheVersion({ force = false } = {}) {
	if (!force) {
		const cached = getMemoryCache(CACHE_KEY);
		if (cached) {
			return cached;
		}
	}

	const response = await cacheVersionResource.fetch();
	const normalized = normalizeVersionPayload(
		unwrapPayload(response ?? cacheVersionResource.data)
	);

	return setMemoryCache(CACHE_KEY, normalized, {
		maxAge: CACHE_MAX_AGE.REFERENCE_DATA_VERSION,
		tags: [CACHE_TAGS.REFERENCE_VERSION],
	});
}

export { CACHE_VERSION_ENDPOINT };
