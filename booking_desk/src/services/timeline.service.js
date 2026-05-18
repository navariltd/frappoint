import { fetchAppointmentsByDateRange } from "@/api/appointment.api";
import { fetchProviders } from "@/api/provider.api";

const formatTime = (value) => {
	if (!value) {
		return "00:00";
	}
	const [hh = "00", mm = "00"] = String(value).split(":");
	return `${hh.padStart(2, "0")}:${mm.padStart(2, "0")}`;
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

	return {
		id: row.name,
		providerId: row.appointment_provider,
		guestName: row.full_name || row.customer || "Guest",
		service: row.appointment_type || "Service",
		startTime: formatTime(row.start_time),
		duration: durationHours,
		status: row.status || "Open",
		delayed: "",
		showTimer: String(row.status || "").toLowerCase() === "ongoing",
		date: row.appointment_date,
	};
};

export async function fetchTimelineDataset({ fromDate, toDate }) {
	const [providersRaw, appointmentsRaw] = await Promise.all([
		fetchProviders(),
		fetchAppointmentsByDateRange({ fromDate, toDate }),
	]);

	const providers = providersRaw.map(mapProvider);
	const appointments = appointmentsRaw.map(mapAppointment);

	return {
		providers,
		appointments,
	};
}
