<template>
	<div class="px-6 py-5 space-y-5 max-w-[1100px]">
		<header class="flex flex-wrap items-start justify-between gap-3">
			<div>
				<h1 class="text-[22px] font-semibold text-on-surface">Guest history</h1>
				<p v-if="tab === 'matches'" class="text-[13px] text-on-surface-variant">
					Guests on appointments booked before the hotel, matched to a Guest Profile by
					email or phone. Their history counts towards suggestions only once you confirm
					the match.
				</p>
			</div>
			<button
				v-if="tab === 'matches'"
				type="button"
				class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
				:disabled="busy"
				@click="findMore"
			>
				Find matches
			</button>
		</header>

		<div
			class="flex gap-1 rounded-xl border border-outline-variant bg-surface-container-lowest p-1"
			role="tablist"
		>
			<button
				v-for="option in TABS"
				:key="option.key"
				type="button"
				role="tab"
				:aria-selected="tab === option.key"
				class="flex-1 rounded-lg px-3 py-2 text-[13px] font-semibold"
				:class="
					tab === option.key
						? 'bg-primary text-on-primary'
						: 'text-on-surface-variant hover:bg-surface-container-high'
				"
				@click="tab = option.key"
			>
				{{ option.label }}
			</button>
		</div>

		<DuplicateGuests v-if="tab === 'duplicates'" />
		<template v-else>
			<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
				{{ error }}
			</p>
			<p v-if="found !== null" class="text-[13px] text-on-surface-variant">
				{{
					found
						? `${found} new match${found === 1 ? "" : "es"} to review.`
						: "No new matches. Guests whose email or phone fits more than one profile are left out."
				}}
			</p>
			<LoadFailed
				v-if="loadError"
				what="matches to review"
				:reason="loadError"
				:busy="loading"
				@retry="loadMatches"
			/>
			<p v-else-if="!loaded" class="text-[13px] text-on-surface-variant">Loading…</p>
			<p
				v-else-if="!matches.length"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-center text-[13px] text-on-surface-variant"
			>
				Nothing to review.
			</p>

			<ul
				v-else
				class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
			>
				<li
					v-for="match in matches"
					:key="match.name"
					class="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
				>
					<div class="min-w-0 text-[13px]">
						<p>
							<b>{{ match.guest_name || "Unnamed guest" }}</b>
							<span class="text-on-surface-variant">
								· {{ match.service_type }} ·
								{{ formatNight(match.appointment_date) }}</span
							>
						</p>
						<p class="text-[12px] text-on-surface-variant">
							{{ [match.email, match.mobile_no].filter(Boolean).join(" · ") }}
						</p>
						<p class="text-[12px]">
							→ <b>{{ match.profile_name }}</b>
							<span class="text-on-surface-variant">
								({{ match.guest_profile }}) · matched on
								{{ match.match_basis }}</span
							>
						</p>
					</div>
					<div class="flex gap-2">
						<button
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="review(match, false)"
						>
							Not the same
						</button>
						<button
							type="button"
							class="rounded-lg bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="review(match, true)"
						>
							Same guest
						</button>
					</div>
				</li>
			</ul>
		</template>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import {
	fetchHistoryMatchesApi,
	findHistoryMatchesApi,
	hotelErrorMessage,
	reviewHistoryMatchApi,
} from "@/api/hotel.api";
import DuplicateGuests from "@/components/hotel/DuplicateGuests.vue";
import LoadFailed from "@/components/hotel/LoadFailed.vue";
import { formatNight } from "@/utils/hotelFormat";

const TABS = [
	{ key: "matches", label: "Appointment matches" },
	{ key: "duplicates", label: "Duplicate profiles" },
];
const tab = ref("matches");
const matches = ref([]);
const found = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
// The queue failed to load: shown instead of "Nothing to review", which would be untrue.
const loadError = ref("");
const loaded = ref(false);

async function call(command, flag) {
	flag.value = true;
	error.value = "";
	try {
		const data = await command();
		matches.value = data?.matches || [];
		return data;
	} catch (e) {
		error.value = hotelErrorMessage(e);
		return null;
	} finally {
		flag.value = false;
	}
}

async function findMore() {
	const data = await call(findHistoryMatchesApi, busy);
	if (data) found.value = data.created;
}

function review(match, confirm) {
	call(() => reviewHistoryMatchApi(match.name, confirm), busy);
}

async function loadMatches() {
	loading.value = true;
	try {
		matches.value = (await fetchHistoryMatchesApi())?.matches || [];
		loaded.value = true;
		loadError.value = "";
	} catch (e) {
		loadError.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

onMounted(loadMatches);
</script>
