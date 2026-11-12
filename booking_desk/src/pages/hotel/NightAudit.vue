<template>
	<div class="px-6 py-5 space-y-5 max-w-5xl">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<template v-else>
			<p v-if="loading && !data" class="text-[13px] text-on-surface-variant">Loading…</p>
			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>
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
						class="rounded-xl border px-4 py-3"
						:class="
							data.preview.arrivals_not_checked_in
								? 'border-tertiary bg-tertiary-container/20'
								: 'border-outline-variant bg-surface-container-lowest'
						"
					>
						<p class="text-[11px] text-on-surface-variant">Arrivals not checked in</p>
						<p class="text-[20px] font-semibold">
							{{ data.preview.arrivals_not_checked_in }}
						</p>
						<p class="text-[12px] text-on-surface-variant">
							Listed as no-show candidates. They are not charged tonight.
						</p>
					</div>
					<div
						class="rounded-xl border px-4 py-3"
						:class="
							data.preview.departures_not_checked_out
								? 'border-tertiary bg-tertiary-container/20'
								: 'border-outline-variant bg-surface-container-lowest'
						"
					>
						<p class="text-[11px] text-on-surface-variant">
							Departures not checked out
						</p>
						<p class="text-[20px] font-semibold">
							{{ data.preview.departures_not_checked_out }}
						</p>
						<p class="text-[12px] text-on-surface-variant">
							Check them out or extend them before the audit.
						</p>
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
							</tr>
						</tbody>
					</table>
				</section>
			</template>
		</template>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { fetchNightAuditApi, hotelErrorMessage, startNightAuditApi } from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { addDays, formatMoney, formatNight } from "@/utils/hotelFormat";

const POLL_MS = 2000;
const ACTIVE = ["Queued", "Running"];

const hotel = useHotelStore();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
let timer = null;

const run = computed(() => data.value?.run || null);
const isActive = computed(() => ACTIVE.includes(run.value?.status));
// A failed run, or one whose worker died, can be started again.
const canStart = computed(
	() =>
		data.value?.can_start &&
		(!run.value || run.value.status === "Failed" || (isActive.value && !run.value.job_active))
);
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
	if (isActive.value && run.value?.job_active) timer = setTimeout(poll, POLL_MS);
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
		if (!quiet) error.value = "";
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
		schedulePoll();
	}
}

async function start() {
	const preview = data.value.preview;
	const warnings = [];
	if (preview.arrivals_not_checked_in)
		warnings.push(`${preview.arrivals_not_checked_in} arrival(s) not checked in`);
	if (preview.departures_not_checked_out)
		warnings.push(`${preview.departures_not_checked_out} departure(s) not checked out`);
	const answer = await ask({
		tone: warnings.length ? "danger" : "warning",
		title: `${run.value ? "Restart" : "Start"} night audit for ${formatNight(
			data.value.business_date
		)}?`,
		message:
			`It posts ${preview.room_nights} room night(s) and moves the business date to ` +
			`${formatNight(addDays(data.value.business_date, 1))}.` +
			(warnings.length ? ` Still open: ${warnings.join(", ")}.` : ""),
		confirmLabel: run.value ? "Restart" : "Start night audit",
	});
	if (!answer) return;
	busy.value = true;
	error.value = "";
	try {
		data.value = await startNightAuditApi(hotel.property);
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
onBeforeUnmount(() => clearTimeout(timer));
watch(
	() => hotel.property,
	() => load()
);
</script>
