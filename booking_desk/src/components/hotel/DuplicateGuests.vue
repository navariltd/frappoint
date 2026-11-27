<template>
	<section class="space-y-4" aria-label="Duplicate profiles">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<p class="max-w-[640px] text-[13px] text-on-surface-variant">
				Profiles that may be the same person: the same email or phone, or the same name
				with a date of birth or nationality. A name-only match is only a possibility.
				Nothing is merged until someone allowed to merges it, with a reason; a merge can be
				undone.
			</p>
			<button
				type="button"
				class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
				:disabled="busy"
				@click="findMore"
			>
				Find duplicates
			</button>
		</div>

		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
			{{ error }}
		</p>
		<p v-if="found !== null" class="text-[13px] text-on-surface-variant">
			{{ found ? `${found} new pair${found === 1 ? "" : "s"} to review.` : "No new pairs." }}
		</p>

		<LoadFailed
			v-if="loadError"
			what="duplicate profiles"
			:reason="loadError"
			:busy="loading"
			@retry="load"
		/>
		<p v-else-if="!data" class="text-[13px] text-on-surface-variant">Loading…</p>
		<template v-else>
			<p
				v-if="!data.duplicates.length"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-center text-[13px] text-on-surface-variant"
			>
				No possible duplicates to review.
			</p>
			<ul
				v-else
				class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
			>
				<li v-for="row in data.duplicates" :key="row.name" class="px-4 py-3 space-y-2">
					<div class="flex flex-wrap items-center justify-between gap-3">
						<p class="text-[13px]">
							<b>{{ row.profile_name }}</b>
							<span class="text-on-surface-variant"> and </span>
							<b>{{ row.duplicate_name }}</b>
							<span
								class="ml-2 rounded-full px-2 py-0.5 text-[11px] font-semibold"
								:class="
									row.strength === 'Strong'
										? 'bg-secondary-container text-on-secondary-container'
										: 'bg-tertiary-container text-on-tertiary-container'
								"
								>{{ row.strength }}: {{ row.basis }}</span
							>
						</p>
						<button
							type="button"
							class="text-[12px] font-semibold text-primary"
							:disabled="busy"
							@click="toggle(row)"
						>
							{{ open?.name === row.name ? "Close" : "Compare" }}
						</button>
					</div>

					<!-- Side by side: what each holds, and what the merge would keep -->
					<div v-if="open?.name === row.name" class="space-y-3">
						<p
							v-for="warning in open.warnings"
							:key="warning"
							class="rounded-lg bg-tertiary-container/30 px-3 py-2 text-[12px]"
						>
							{{ warning }}
						</p>
						<div class="grid gap-3 sm:grid-cols-2">
							<div
								v-for="profile in open.profiles"
								:key="profile.name"
								class="rounded-lg border px-3 py-2 text-[12px]"
								:class="
									keep === profile.name
										? 'border-primary bg-primary/5'
										: 'border-outline-variant'
								"
							>
								<p class="text-[13px] font-semibold">
									{{ profile.full_name }}
									<span class="font-normal text-on-surface-variant">
										· {{ profile.name }}</span
									>
								</p>
								<dl class="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
									<template v-for="field in FIELDS" :key="field.key">
										<dt class="text-on-surface-variant">{{ field.label }}</dt>
										<dd>{{ show(profile[field.key], field) }}</dd>
									</template>
								</dl>
								<label
									v-if="open.can_merge"
									class="mt-2 flex items-center gap-2 font-semibold"
								>
									<input v-model="keep" type="radio" :value="profile.name" />
									Keep this profile
								</label>
							</div>
						</div>
						<div class="flex flex-wrap justify-end gap-2">
							<button
								type="button"
								class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
								:disabled="busy"
								@click="notDuplicate(row)"
							>
								Different people
							</button>
							<button
								v-if="open.can_merge"
								type="button"
								class="rounded-lg bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
								:disabled="busy || !keep"
								@click="merge(row)"
							>
								Merge into the kept profile
							</button>
						</div>
					</div>
				</li>
			</ul>

			<!-- The latest merges, each with its undo -->
			<div v-if="data.recent_merges.length" class="space-y-1.5">
				<h2 class="text-[13px] font-semibold">Recent merges</h2>
				<ul class="space-y-1 text-[12px]">
					<li
						v-for="merge in data.recent_merges"
						:key="merge.name"
						class="flex flex-wrap items-center justify-between gap-2"
					>
						<span>
							<b>{{ merge.source_name }}</b> into <b>{{ merge.target_name }}</b>
							<span class="text-on-surface-variant">
								· {{ merge.moved_count }} record{{
									merge.moved_count === 1 ? "" : "s"
								}}
								moved · {{ merge.merged_by }}</span
							>
						</span>
						<button
							v-if="data.can_merge"
							type="button"
							class="font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							@click="unmerge(merge)"
						>
							Unmerge
						</button>
					</li>
				</ul>
			</div>
		</template>
	</section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import {
	compareDuplicateGuestsApi,
	fetchDuplicateGuestsApi,
	findDuplicateGuestsApi,
	hotelErrorMessage,
	markNotDuplicateApi,
	mergeGuestsApi,
	unmergeGuestsApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import LoadFailed from "@/components/hotel/LoadFailed.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatNight } from "@/utils/hotelFormat";

// What the reviewer compares. Date of birth comes only for roles that see sensitive details.
const FIELDS = [
	{ key: "email", label: "Email" },
	{ key: "mobile_no", label: "Phone" },
	{ key: "nationality", label: "Nationality" },
	{ key: "date_of_birth", label: "Born", date: true },
	{ key: "customer", label: "Customer" },
	{ key: "stays", label: "Stays" },
	{ key: "last_stay", label: "Last stay", date: true },
	{ key: "folios", label: "Folios paid" },
	{ key: "services", label: "Services" },
	{ key: "preferences", label: "Preferences" },
	{ key: "creation", label: "Created", date: true },
];

const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const open = ref(null);
const keep = ref("");
const found = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const loadError = ref("");

function show(value, field) {
	if (value === null || value === undefined || value === "") return "–";
	return field.date ? formatNight(String(value).slice(0, 10)) : value;
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		const result = await command();
		if (result?.duplicates) data.value = result;
		return result;
	} catch (e) {
		error.value = hotelErrorMessage(e);
		return null;
	} finally {
		busy.value = false;
	}
}

async function load() {
	loading.value = true;
	try {
		data.value = await fetchDuplicateGuestsApi();
		loadError.value = "";
	} catch (e) {
		loadError.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function findMore() {
	const result = await run(findDuplicateGuestsApi);
	if (result) found.value = result.created;
}

async function toggle(row) {
	if (open.value?.name === row.name) {
		open.value = null;
		return;
	}
	const comparison = await run(() => compareDuplicateGuestsApi(row.name));
	if (!comparison) return;
	open.value = comparison;
	// Keep the profile with more history by default; the reviewer can choose the other.
	const [first, second] = comparison.profiles;
	keep.value =
		second.stays + second.folios > first.stays + first.folios ? second.name : first.name;
}

async function merge(row) {
	const kept = open.value.profiles.find((profile) => profile.name === keep.value);
	const away = open.value.profiles.find((profile) => profile.name !== keep.value);
	const answer = await ask({
		title: `Merge ${away.full_name} into ${kept.full_name}?`,
		message: `Stays, folios, preferences and history move to ${kept.name}; ${away.name} is kept, marked as merged. The merge is recorded and can be undone.`,
		reasonLabel: "Why are they the same person?",
		confirmLabel: "Merge",
		tone: "warning",
	});
	if (!answer) return;
	const result = await run(() => mergeGuestsApi(row.name, kept.name, answer.reason));
	if (result) {
		open.value = null;
		notify({ title: `Merged into ${kept.full_name}`, tone: "info" });
	}
}

async function notDuplicate(row) {
	const answer = await ask({
		title: `${row.profile_name} and ${row.duplicate_name} are different people?`,
		message: "They won't be proposed as duplicates again.",
		reasonLabel: "How you know (optional is fine)",
		confirmLabel: "Different people",
	});
	if (!answer) return;
	const result = await run(() => markNotDuplicateApi(row.name, answer.reason));
	if (result) open.value = null;
}

async function unmerge(merge) {
	const answer = await ask({
		title: `Unmerge ${merge.source_name} from ${merge.target_name}?`,
		message:
			"Exactly the records the merge moved go back, and the details it filled in are cleared.",
		reasonLabel: "Why",
		confirmLabel: "Unmerge",
		tone: "warning",
	});
	if (answer) run(() => unmergeGuestsApi(merge.name, answer.reason));
}

onMounted(load);
</script>
