import { defineStore } from "pinia";
import {
	buildTimelineView,
	computeEffectiveDuration,
	computePauseDuration,
	fetchAppointmentEventLogs,
	normalizeAppointmentEventLog,
	normalizeTimeTracking,
} from "@/services/appointmentEventLogs.service";

let tickerHandle = null;

const findOpenSession = (logs) =>
	(logs.findLast?.((log) => !log.endTime && ["Start", "Resume", "Pause"].includes(log.logType)) ||
		[...logs].reverse().find((log) => !log.endTime && ["Start", "Resume", "Pause"].includes(log.logType)) ||
		null);

export const useAppointmentEventLogsStore = defineStore("appointmentEventLogs", {
	state: () => ({
		logs: [],
		activeSession: null,
		isPaused: false,
		isRunning: false,
		currentDuration: 0,
		totalPauseSeconds: 0,
		pauseSegments: [],
	}),
	getters: {
		timelineSegments(state) {
			return buildTimelineView(state.logs);
		},
	},
	actions: {
		stopTicker() {
			if (tickerHandle) {
				clearInterval(tickerHandle);
				tickerHandle = null;
			}
		},
		refreshLiveState() {
			this.currentDuration = computeEffectiveDuration(this.logs);
			this.totalPauseSeconds = computePauseDuration(this.logs);
			this.activeSession = findOpenSession(this.logs);
			this.isPaused = Boolean(this.activeSession?.logType === "Pause");
			this.isRunning = Boolean(
				this.activeSession && ["Start", "Resume"].includes(this.activeSession.logType)
			);
		},
		startTicker() {
			this.stopTicker();
			if (!this.isRunning && !this.isPaused) {
				return;
			}
			tickerHandle = setInterval(() => {
				this.refreshLiveState();
			}, 1000);
		},
		hydrateFromPayload(logs = [], timeTracking = {}) {
			this.logs = logs.map(normalizeAppointmentEventLog);
			const normalized = normalizeTimeTracking(timeTracking, this.logs);
			this.activeSession = normalized.activeSession;
			this.isPaused = normalized.isPaused;
			this.isRunning = normalized.isRunning;
			this.currentDuration = normalized.effectiveDurationSeconds;
			this.totalPauseSeconds = normalized.totalPauseSeconds;
			this.pauseSegments = normalized.pauseSegments;
			this.startTicker();
		},
		async fetchLogs(appointmentId) {
			const payload = await fetchAppointmentEventLogs(appointmentId);
			this.hydrateFromPayload(payload.logs, payload.timeTracking);
		},
		reset() {
			this.stopTicker();
			this.logs = [];
			this.activeSession = null;
			this.isPaused = false;
			this.isRunning = false;
			this.currentDuration = 0;
			this.totalPauseSeconds = 0;
			this.pauseSegments = [];
		},
	},
});