const memoryCache = new Map();

export const CACHE_MAX_AGE = {
	SHORT: 30 * 1000,
	DASHBOARD: 45 * 1000,
	MEDIUM: 5 * 60 * 1000,
	REFERENCE_DATA_VERSION: 15 * 1000,
	WORKFLOW_STATE: 15 * 60 * 1000,
};

export const CACHE_TAGS = {
	SERVICES: "services",
	PROVIDERS: "providers",
	DASHBOARD: "dashboard",
	BOOKINGS: "bookings",
	WORKFLOW: "workflow",
	REFERENCE_VERSION: "reference-version",
};

const normalizeTags = (tags = []) =>
	Array.from(new Set((Array.isArray(tags) ? tags : [tags]).filter(Boolean)));

const isExpired = (entry, now = Date.now()) => now - entry.createdAt > entry.maxAge;

const normalizeMaxAge = (maxAge) => {
	const value = Number(maxAge);
	if (!Number.isFinite(value) || value <= 0) {
		return 0;
	}
	return value;
};

export function setMemoryCache(key, value, { maxAge, tags = [], version = "" } = {}) {
	if (!key) return value;

	memoryCache.set(key, {
		value,
		createdAt: Date.now(),
		maxAge: normalizeMaxAge(maxAge),
		version: version || "",
		tags: normalizeTags(tags),
	});

	return value;
}

export function getMemoryCache(key, { version = "" } = {}) {
	if (!key) return null;

	const entry = memoryCache.get(key);
	if (!entry) return null;

	if (isExpired(entry)) {
		memoryCache.delete(key);
		return null;
	}

	if (version && entry.version && entry.version !== version) {
		memoryCache.delete(key);
		return null;
	}

	return entry.value;
}

export function invalidateMemoryCacheByKey(key) {
	if (!key) return;
	memoryCache.delete(key);
}

export function invalidateMemoryCacheByTag(tag) {
	if (!tag) return;

	for (const [key, entry] of memoryCache.entries()) {
		if (entry.tags?.includes(tag)) {
			memoryCache.delete(key);
		}
	}
}

export function clearMemoryCache() {
	memoryCache.clear();
}

export function sweepExpiredMemoryCache() {
	const now = Date.now();
	for (const [key, entry] of memoryCache.entries()) {
		if (isExpired(entry, now)) {
			memoryCache.delete(key);
		}
	}
}

export function getMemoryCacheMeta(key) {
	const entry = memoryCache.get(key);
	if (!entry) {
		return null;
	}

	const now = Date.now();
	const age = now - entry.createdAt;
	return {
		createdAt: entry.createdAt,
		maxAge: entry.maxAge,
		age,
		isExpired: age > entry.maxAge,
		version: entry.version,
		tags: entry.tags,
	};
}
