import { fetchAppointmentsByDateRange } from "@/api/appointment.api";
import { fetchProviders, fetchProvidersByIds } from "@/api/provider.api";

const formatTime = (value) => {
	if (!value) {
		return "00:00";
	}

	const raw = String(value).trim().toLowerCase();
	const ampmMatch = raw.match(/^(\d{1,2})(?::(\d{1,2}))?(?::\d{1,2})?\s*(am|pm)$/i);
	if (ampmMatch) {
		const hour12 = Number(ampmMatch[1]);
		const minute = Number(ampmMatch[2] || 0);
		const suffix = ampmMatch[3].toLowerCase();
		let hour24 = hour12 % 12;
		if (suffix === "pm") {
			hour24 += 12;
		}
		return `${String(hour24).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
	}

	const hmsMatch = raw.match(/^(\d{1,2})(?::(\d{1,2}))?(?::\d{1,2})?/);
	if (hmsMatch) {
		const hh = Number(hmsMatch[1]);
		const mm = Number(hmsMatch[2] || 0);
		return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
	}

	return "00:00";
};

const toInitials = (name) => {
	if (!name) {
		return "SP";
	}
	const words = name.split(" ").filter(Boolean);
	if (!words.length) {
		return "SP";
	}
	return words
		.slice(0, 2)
		.map((word) => word[0]?.toUpperCase() || "")
		.join("");
};

const mapProvider = (row) => {
	const providerName =
		row.provider_name || [row.first_name, row.last_name].filter(Boolean).join(" ") || row.name;
	return {
		id: row.name,
		name: providerName,
		initials: toInitials(providerName),
		designation: row.designation || "Service Provider",
		overloaded: false,
	};
};

const mapAppointment = (row) => {
	const durationMinutes = Number(row.duration) || 60;
	const durationHours = Number((durationMinutes / 60).toFixed(2));
	const rawDate = row.appointment_date ? String(row.appointment_date) : "";
	const normalizedDate = rawDate.includes(" ") ? rawDate.split(" ")[0] : rawDate;
	const providerId = row.appointment_provider || "unassigned";

	return {
		id: row.name,
		providerId,
		guestName: row.full_name || row.customer || "Guest",
		service: row.appointment_type || "Service",
		startTime: formatTime(row.start_time),
		duration: durationHours,
		status: row.status || "Open",
		delayed: "",
		showTimer: String(row.status || "").toLowerCase() === "ongoing",
		date: normalizedDate,
	};
};

export async function fetchTimelineDataset({ fromDate, toDate }) {
	const [providersRaw, appointmentsRaw] = await Promise.all([
		fetchProviders(),
		fetchAppointmentsByDateRange({ fromDate, toDate }),
	]);

	const providers = providersRaw.map(mapProvider);
	const appointments = appointmentsRaw.map(mapAppointment);
	const providerIds = new Set(providers.map((provider) => provider.id));

	const missingProviderIds = Array.from(
		new Set(
			appointments
				.map((appointment) => appointment.providerId)
				.filter((providerId) => providerId && providerId !== "unassigned")
				.filter((providerId) => !providerIds.has(providerId))
		)
	);

	const missingProviderRows = await fetchProvidersByIds(missingProviderIds);
	const missingProviderById = new Map(missingProviderRows.map((row) => [row.name, row]));

	for (const missingProviderId of missingProviderIds) {
		const resolvedProvider = missingProviderById.get(missingProviderId);
		if (resolvedProvider) {
			providers.push(mapProvider(resolvedProvider));
			continue;
		}

		providers.push({
			id: missingProviderId,
			name: missingProviderId,
			initials: toInitials(missingProviderId),
			designation: "Provider not in active list",
			overloaded: false,
		});
	}

	const hasUnassignedAppointments = appointments.some(
		(appointment) => appointment.providerId === "unassigned"
	);

	if (hasUnassignedAppointments && !providerIds.has("unassigned")) {
		providers.push({
			id: "unassigned",
			name: "Unassigned",
			initials: "UA",
			designation: "No provider linked",
			overloaded: false,
		});
	}

	return {
		providers,
		appointments,
	};
}
