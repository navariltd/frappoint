import {
	fetchAppointmentDetailsApi,
	performAppointmentActionApi,
} from "@/api/appointmentDetails.api";

const toNumber = (value) => Number(value || 0);

const toTimestamp = (value) => {
	if (!value) {
		return 0;
	}
	const parsed = new Date(value).getTime();
	return Number.isNaN(parsed) ? 0 : parsed;
};

export function normalizeAppointmentEventLog(raw = {}) {
	return {
		name: raw.name || "",
		appointment: raw.appointment || raw.appointmentId || "",
		booking: raw.booking || raw.bookingId || "",
		logType: raw.logType || raw.log_type || "",
		startTime: raw.startTime || raw.start_time || "",
		endTime: raw.endTime || raw.end_time || "",
		durationSeconds: toNumber(raw.durationSeconds ?? raw.duration_seconds),
		createdBy: raw.createdBy || raw.created_by || "",
		notes: raw.notes || "",
	};
}

function findActiveSession(logs) {
	for (let index = logs.length - 1; index >= 0; index -= 1) {
		const log = logs[index];
		if (!log.endTime && ["Start", "Resume", "Pause"].includes(log.logType)) {
			return log;
		}
	}
	return null;
}

export function computeEffectiveDuration(logs, now = new Date()) {
	const nowMs = now instanceof Date ? now.getTime() : toTimestamp(now);
	return logs.reduce((total, log) => {
		if (!["Start", "Resume"].includes(log.logType)) {
			return total;
		}
		const startMs = toTimestamp(log.startTime);
		const endMs = log.endTime ? toTimestamp(log.endTime) : nowMs;
		if (!startMs || !endMs || endMs <= startMs) {
			return total;
		}
		return total + Math.floor((endMs - startMs) / 1000);
	}, 0);
}

export function computePauseDuration(logs, now = new Date()) {
	const nowMs = now instanceof Date ? now.getTime() : toTimestamp(now);
	return logs.reduce((total, log) => {
		if (log.logType !== "Pause") {
			return total;
		}
		const startMs = toTimestamp(log.startTime);
		const endMs = log.endTime ? toTimestamp(log.endTime) : nowMs;
		if (!startMs || !endMs || endMs <= startMs) {
			return total;
		}
		return total + Math.floor((endMs - startMs) / 1000);
	}, 0);
}

export function buildTimelineView(logs, now = new Date()) {
	const nowMs = now instanceof Date ? now.getTime() : toTimestamp(now);
	return logs.map((log) => {
		const startMs = toTimestamp(log.startTime);
		const endMs = log.endTime ? toTimestamp(log.endTime) : nowMs;
		const durationSeconds =
			log.durationSeconds ||
			(startMs && endMs && endMs > startMs ? Math.floor((endMs - startMs) / 1000) : 0);
		return {
			id: log.name || `${log.logType}-${log.startTime}`,
			label: log.logType,
			startTime: log.startTime,
			endTime: log.endTime,
			durationSeconds,
			isOpen: !log.endTime,
			notes: log.notes,
			createdBy: log.createdBy,
			tone:
				log.logType === "Pause"
					? "pause"
					: log.logType === "End"
						? "end"
						: log.logType === "Check-in"
							? "checkin"
							: "work",
		};
	});
}

export function normalizeTimeTracking(raw = {}, logs = []) {
	const normalizedLogs = logs.map(normalizeAppointmentEventLog);
	const activeSession = raw.activeSession
		? normalizeAppointmentEventLog(raw.activeSession)
		: findActiveSession(normalizedLogs);
	return {
		effectiveDurationSeconds:
			toNumber(raw.effectiveDurationSeconds) || computeEffectiveDuration(normalizedLogs),
		totalPauseSeconds: toNumber(raw.totalPauseSeconds) || computePauseDuration(normalizedLogs),
		pauseSegments: Array.isArray(raw.pauseSegments)
			? raw.pauseSegments.map(normalizeAppointmentEventLog)
			: normalizedLogs.filter((log) => log.logType === "Pause"),
		activeSession,
		isPaused: Boolean(raw.isPaused ?? activeSession?.logType === "Pause"),
		isRunning: Boolean(
			raw.isRunning ?? (activeSession && ["Start", "Resume"].includes(activeSession.logType))
		),
	};
}

export async function fetchAppointmentEventLogs(appointmentId) {
	const payload = (await fetchAppointmentDetailsApi(appointmentId)) || {};
	const logs = Array.isArray(payload.eventLogs) ? payload.eventLogs.map(normalizeAppointmentEventLog) : [];
	return {
		logs,
		timeTracking: normalizeTimeTracking(payload.timeTracking || {}, logs),
	};
}

export async function createAppointmentEventEntry(payload) {
	const response = await performAppointmentActionApi(payload);
	const logs = Array.isArray(response?.eventLogs)
		? response.eventLogs.map(normalizeAppointmentEventLog)
		: [];
	return {
		response,
		logs,
		timeTracking: normalizeTimeTracking(response?.timeTracking || {}, logs),
	};
}