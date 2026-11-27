<template>
	<div class="px-6 py-5 space-y-5 max-w-5xl">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<p v-if="loading && !data && !loadError" class="text-[13px] text-on-surface-variant">
				Loading…
			</p>
			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>
			<LoadFailed
				v-if="loadError"
				:what="data ? 'the latest audit progress' : 'the night audit'"
				:reason="loadError"
				:busy="loading"
				@retry="load()"
			/>
			<ActionBanner
				:banner="banner"
				:busy="busy"
				@confirm="confirmBanner"
				@cancel="cancelBanner"
			/>

			<template v-if="data">
				<header class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<h1 class="text-[22px] font-semibold text-on-surface">Night Audit</h1>
						<p class="text-[13px] text-on-surface-variant">
							Closes business date
							<b class="text-on-surface">{{ formatNight(data.business_date) }}</b>
							· {{ hotel.currentProperty?.property_name || data.property }}
						</p>
					</div>
					<button
						v-if="canStart"
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy"
						@click="start"
					>
						{{ run ? "Restart night audit" : "Start night audit" }}
					</button>
				</header>

				<!-- Tonight -->
				<section class="grid gap-3 sm:grid-cols-3">
					<div
						class="rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-3"
					>
						<p class="text-[11px] text-on-surface-variant">Room nights to post</p>
						<p class="text-[20px] font-semibold">{{ data.preview.room_nights }}</p>
						<p class="text-[12px] text-on-surface-variant">
							{{ formatMoney(data.preview.room_charges, data.currency) }}
						</p>
					</div>
					<div
						class="rounded-xl border px-4 py-3 sm:col-span-2"
						:class="
							unresolved.length
								? 'border-tertiary bg-tertiary-container/20'
								: 'border-outline-variant bg-surface-container-lowest'
						"
					>
						<p class="text-[11px] text-on-surface-variant">Before the audit</p>
						<p class="text-[15px] font-semibold">
							{{
								!data.prechecks.length
									? "Closed"
									: unresolved.length
									? `${unresolved.length} check${
											unresolved.length === 1 ? "" : "s"
									  } to resolve or override`
									: "Ready to close the day"
							}}
						</p>
						<p class="text-[12px] text-on-surface-variant">
							Blocking checks stop the audit until they are fixed, or let pass with a
							reason by a role allowed to. Warnings are recorded in the report.
						</p>
					</div>
				</section>

				<!-- Pre-checks: blocking first, each with what it found and how to get past it -->
				<section
					v-if="data.prechecks.length && (!run || run.status === 'Failed' || !isActive)"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest divide-y divide-outline-variant"
					aria-label="Pre-checks"
				>
					<div
						v-for="check in data.prechecks"
						:key="check.key"
						class="px-4 py-3 space-y-2"
					>
						<div class="flex flex-wrap items-center justify-between gap-2">
							<p class="flex items-center gap-2 text-[13px] font-semibold">
								<span
									class="material-symbols-outlined text-[18px]"
									:class="checkTone(check).icon"
									aria-hidden="true"
									>{{ checkTone(check).symbol }}</span
								>
								{{ check.title }}
								<span
									v-if="check.count"
									class="rounded-full px-2 py-0.5 text-[11px]"
									:class="checkTone(check).badge"
									>{{ check.count }}</span
								>
							</p>
							<span class="text-[11px] text-on-surface-variant">
								{{
									!check.count
										? "Nothing found"
										: check.severity === "Blocking"
										? overridden(check)
											? "Overridden"
											: "Blocking"
										: "Warning"
								}}
							</span>
						</div>
						<template v-if="check.count">
							<p class="text-[12px] text-on-surface-variant">{{ check.hint }}</p>
							<ul class="flex flex-wrap gap-1.5 text-[12px]">
								<li
									v-for="item in check.items"
									:key="`${check.key}-${item.name}-${item.label}`"
									class="rounded bg-surface-container px-2 py-0.5"
								>
									{{ item.label }}
								</li>
								<li
									v-if="check.count > check.items.length"
									class="px-1 text-on-surface-variant"
								>
									and {{ check.count - check.items.length }} more
								</li>
							</ul>
							<template v-if="check.severity === 'Blocking' && !overridden(check)">
								<label
									v-if="check.can_override"
									class="block text-[12px] text-on-surface-variant"
								>
									Let it pass: {{ check.override_consequence }}
									<input
										v-model="reasons[check.key]"
										type="text"
										placeholder="Reason"
										class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-[13px] text-on-surface"
									/>
								</label>
								<p v-else class="text-[12px] text-on-surface-variant">
									Only {{ check.override_roles.join(", ") }} can let this pass.
								</p>
							</template>
						</template>
					</div>
				</section>

				<!-- Tonight's run -->
				<section
					v-if="run"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
				>
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div class="flex items-center gap-3">
							<h2 class="text-[15px] font-semibold">{{ run.name }}</h2>
							<HotelStatusBadge :status="run.status" />
							<span
								v-if="isActive && !run.job_active"
								class="text-[12px] text-error"
							>
								The background job is not running. Restart the audit.
							</span>
						</div>
						<p class="text-[12px] text-on-surface-variant">
							Started by {{ run.started_by }}
							<template v-if="run.attempts > 1">
								· attempt {{ run.attempts }}</template
							>
						</p>
					</div>
					<p v-if="run.error" class="text-[12px] text-error">{{ run.error }}</p>

					<ol class="space-y-2">
						<li
							v-for="(stage, index) in run.stages"
							:key="stage.stage"
							class="rounded-lg border border-outline-variant px-3 py-2"
						>
							<div class="flex flex-wrap items-center justify-between gap-2">
								<p class="text-[13px] font-semibold">
									{{ index + 1 }}. {{ stage.stage }}
								</p>
								<span class="flex items-center gap-3 text-[12px]">
									<span v-if="stage.posted || stage.skipped || stage.failed">
										{{ stage.posted }} done
										<template v-if="stage.skipped">
											· {{ stage.skipped }} already done</template
										>
										<template v-if="stage.failed">
											·
											<b class="text-error">{{ stage.failed }} failed</b>
										</template>
									</span>
									<span
										class="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
										:class="stageClass(stage.status)"
										>{{ stage.status }}</span
									>
								</span>
							</div>
							<p
								v-if="stage.message"
								class="mt-1 text-[12px] text-on-surface-variant"
							>
								{{ stage.message }}
							</p>
						</li>
					</ol>

					<div v-if="run.overrides?.length" class="space-y-1">
						<p class="text-[12px] font-semibold">Let pass</p>
						<ul class="space-y-0.5 text-[12px] text-on-surface-variant">
							<li v-for="row in run.overrides" :key="row.check_key">
								<b class="text-on-surface">{{ row.check_title }}</b>
								({{ row.found }}) by {{ row.overridden_by }} as {{ row.role }}:
								{{ row.reason }}
							</li>
						</ul>
					</div>

					<!-- The books didn't agree: investigate and run again, or a manager lets it pass -->
					<label
						v-if="
							run.status === 'Failed' &&
							run.reconciliation_failed &&
							data.can_override_reconciliation
						"
						class="block text-[12px] text-on-surface-variant"
					>
						Let the differences pass: {{ data.reconciliation_override_consequence }}
						<input
							v-model="reasons.reconciliation"
							type="text"
							placeholder="Reason (leave empty to check again after fixing)"
							class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-[13px] text-on-surface"
						/>
					</label>
				</section>

				<!-- The closed day's figures, kept on the run -->
				<section
					v-if="shownReport"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
				>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<h2 class="text-[15px] font-semibold">
							Audit report · {{ formatNight(shownReport.business_date) }}
						</h2>
						<button
							v-if="viewed"
							type="button"
							class="text-[12px] font-semibold text-primary"
							@click="viewed = null"
						>
							Close
						</button>
					</div>
					<AuditReport :report="shownReport" />
				</section>

				<!-- History -->
				<section
					v-if="data.recent_runs.length"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				>
					<h2 class="text-[15px] font-semibold">Recent audits</h2>
					<table class="mt-2 w-full text-[12px]">
						<tbody>
							<tr
								v-for="past in data.recent_runs"
								:key="past.name"
								class="border-b border-outline-variant"
							>
								<td class="py-1.5">{{ formatNight(past.business_date) }}</td>
								<td class="py-1.5">{{ past.status }}</td>
								<td class="py-1.5 text-on-surface-variant">
									{{ past.started_by }}
								</td>
								<td class="py-1.5 text-right text-on-surface-variant">
									{{ formatTimestamp(past.finished_at) }}
								</td>
								<td class="py-1.5 text-right">
									<button
										v-if="past.report_generated_at"
										type="button"
										class="font-semibold text-primary disabled:opacity-50"
										:disabled="reportLoading"
										@click="viewReport(past)"
									>
										Report
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</section>

				<!-- Desk reports, opened with this property already chosen -->
				<section
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				>
					<h2 class="text-[15px] font-semibold">Reports</h2>
					<ul class="mt-2 grid gap-1.5 sm:grid-cols-2 text-[13px]">
						<li v-for="report in REPORTS" :key="report.name">
							<a
								:href="reportUrl(report.name)"
								target="_blank"
								rel="noopener"
								class="font-semibold text-primary"
								>{{ report.name }}</a
							>
							<span class="text-[12px] text-on-surface-variant">
								· {{ report.about }}</span
							>
						</li>
					</ul>
				</section>
			</template>
		</template>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import {
	fetchAuditReportApi,
	fetchNightAuditApi,
	hotelErrorMessage,
	startNightAuditApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import AuditReport from "@/components/hotel/AuditReport.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import LoadFailed from "@/components/hotel/LoadFailed.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useSocket } from "@/socket";
import { useHotelStore } from "@/stores/hotel.store";
import { addDays, formatMoney, formatNight } from "@/utils/hotelFormat";

const POLL_MS = 2000;
// With live updates, polling only catches what the socket missed.
const FALLBACK_POLL_MS = 15000;
const RUN_DOCTYPE = "Night Audit Run";
const PROGRESS_EVENT = "hospitality_night_audit";
// The desk reports managers run the hotel on (§24). Each opens for the current property.
const REPORTS = [
	{ name: "Front Desk Movements", about: "arrivals, departures, in house, no-shows" },
	{ name: "House Position", about: "rooms available by type and night" },
	{ name: "Occupancy and Revenue", about: "occupancy, ADR and RevPAR by night" },
	{ name: "Guest Ledger", about: "every open folio and its balance" },
	{ name: "Open Folio Balances", about: "what departed guests still owe" },
	{ name: "Deposits Held", about: "deposits received and not yet applied" },
	{ name: "Cashier Report", about: "shifts by mode: expected, counted, variance" },
	{ name: "Charges and Adjustments", about: "lines posted, reversals, manual postings" },
	{ name: "Settlement Pending Folios", about: "invoices that failed to submit" },
];
const ACTIVE = ["Queued", "Running"];

const hotel = useHotelStore();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
// The audit status itself failed to load (as opposed to starting a run).
const loadError = ref("");
// Reasons typed for letting blocking checks pass, by check key.
const reasons = reactive({});
// A past run's report opened from the history.
const viewed = ref(null);
const reportLoading = ref(false);
let timer = null;

const run = computed(() => data.value?.run || null);
const isActive = computed(() => ACTIVE.includes(run.value?.status));
// A failed run, or one whose worker died, can be started again.
const canStart = computed(
	() =>
		data.value?.can_start &&
		(!run.value || run.value.status === "Failed" || (isActive.value && !run.value.job_active))
);
function overridden(check) {
	return (run.value?.overrides || []).some((row) => row.check_key === check.key);
}
// Blocking checks that found something and have neither an override nor a reason typed yet.
const unresolved = computed(() =>
	(data.value?.prechecks || []).filter(
		(check) =>
			check.severity === "Blocking" &&
			check.count &&
			!overridden(check) &&
			!(reasons[check.key] || "").trim()
	)
);
const shownReport = computed(() => viewed.value || run.value?.audit_report || null);

function checkTone(check) {
	if (!check.count) {
		return { symbol: "check_circle", icon: "text-primary", badge: "" };
	}
	if (check.severity === "Blocking" && !overridden(check)) {
		return {
			symbol: "block",
			icon: "text-error",
			badge: "bg-error-container text-on-error-container",
		};
	}
	return {
		symbol: "warning",
		icon: "text-tertiary",
		badge: "bg-tertiary-container text-on-tertiary-container",
	};
}

function reportUrl(name) {
	return `/app/query-report/${encodeURIComponent(name)}?property=${encodeURIComponent(
		hotel.property || ""
	)}`;
}

async function viewReport(past) {
	reportLoading.value = true;
	error.value = "";
	try {
		viewed.value = (await fetchAuditReportApi(past.name))?.report || null;
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		reportLoading.value = false;
	}
}

const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

function stageClass(status) {
	return (
		{
			Completed: "bg-secondary-container text-on-secondary-container",
			Running: "bg-primary/10 text-primary",
			Failed: "bg-error-container text-on-error-container",
		}[status] || "bg-surface-container text-on-surface-variant"
	);
}

function formatTimestamp(value) {
	if (!value) return "";
	return new Date(String(value).replace(" ", "T")).toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function schedulePoll() {
	clearTimeout(timer);
	// Keep following an active run even when its job looks lost: a worker that picks it up a
	// moment later, or finishes it, clears the warning without a reload.
	if (isActive.value) timer = setTimeout(poll, socket?.connected ? FALLBACK_POLL_MS : POLL_MS);
}

// Live progress: Frappe's realtime room for the run (the server checks the user may read it).
// The audit publishes there at every stage, so the page reloads when something happens.
const socket = useSocket();
let followed = null;

function follow(runName) {
	if (!socket || followed === runName) return;
	if (followed) socket.emit("doc_unsubscribe", RUN_DOCTYPE, followed);
	followed = runName || null;
	if (followed) socket.emit("doc_subscribe", RUN_DOCTYPE, followed);
}

function onProgress(message) {
	if (message?.run && message.run === followed) poll();
}

async function poll() {
	const before = data.value;
	await load({ quiet: true });
	// The run finished: the business date moved, so refresh it everywhere (the top bar too).
	if (before?.run && ACTIVE.includes(before.run.status) && !isActive.value) {
		const finished = data.value?.recent_runs?.find((past) => past.name === before.run.name);
		await hotel.load(true);
		if (finished?.status === "Completed") {
			notify({
				title: `Night audit closed ${formatNight(before.business_date)}`,
				message: `The business date is now ${formatNight(data.value.business_date)}.`,
			});
		}
	}
}

async function load({ quiet = false } = {}) {
	if (!hotel.property) return;
	if (!quiet) loading.value = true;
	try {
		data.value = await fetchNightAuditApi(hotel.property);
		follow(data.value?.run?.name);
		loadError.value = "";
		if (!quiet) error.value = "";
	} catch (e) {
		loadError.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
		schedulePoll();
	}
}

async function start() {
	if (unresolved.value.length) {
		error.value = `Resolve these first, or give a reason to let them pass: ${unresolved.value
			.map((check) => check.title)
			.join(", ")}.`;
		return;
	}
	const overrides = Object.fromEntries(
		Object.entries(reasons)
			.map(([key, reason]) => [key, (reason || "").trim()])
			.filter(([, reason]) => reason)
	);
	const passing = (data.value.prechecks || [])
		.filter((check) => overrides[check.key] && check.count)
		.map((check) => `${check.title} (${check.count})`);
	const answer = await ask({
		tone: passing.length ? "danger" : "warning",
		title: `${run.value ? "Restart" : "Start"} night audit for ${formatNight(
			data.value.business_date
		)}?`,
		message:
			`It posts ${data.value.preview.room_nights} room night(s), reconciles the day and ` +
			`moves the business date to ${formatNight(addDays(data.value.business_date, 1))}.` +
			(passing.length ? ` Letting pass: ${passing.join(", ")}.` : ""),
		confirmLabel: run.value ? "Restart" : "Start night audit",
	});
	if (!answer) return;
	busy.value = true;
	error.value = "";
	try {
		data.value = await startNightAuditApi(hotel.property, overrides);
		follow(data.value?.run?.name);
		Object.keys(reasons).forEach((key) => delete reasons[key]);
	} catch (e) {
		const message = hotelErrorMessage(e);
		await load();
		error.value = message;
	} finally {
		busy.value = false;
		schedulePoll();
	}
}

onMounted(async () => {
	await hotel.load();
	load();
});
socket?.on(PROGRESS_EVENT, onProgress);
onBeforeUnmount(() => {
	clearTimeout(timer);
	socket?.off(PROGRESS_EVENT, onProgress);
	follow(null);
});
watch(
	() => hotel.property,
	() => load()
);
</script>
