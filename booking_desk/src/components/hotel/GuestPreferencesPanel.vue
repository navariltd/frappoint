<template>
	<section
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
	>
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-[15px] font-semibold">Preferences</h2>
			<button
				v-if="insights?.can_edit && editable && !form.open"
				type="button"
				class="text-[12px] font-semibold text-primary"
				@click="openForm"
			>
				+ Add
			</button>
		</div>

		<p v-if="loading && !insights" class="text-[13px] text-on-surface-variant">Loading…</p>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-3 py-2 text-[12px]">
			{{ error }}
		</p>
		<p v-if="insights && !insights.guest_profile" class="text-[13px] text-on-surface-variant">
			Pick the guest's profile to see their preferences.
		</p>

		<template v-if="insights?.guest_profile">
			<!-- Declared: what the guest asked for on every stay -->
			<div class="space-y-1.5">
				<p class="text-[12px] font-semibold text-on-surface">Every stay</p>
				<p v-if="!insights.declared.length" class="text-[12px] text-on-surface-variant">
					Nothing declared yet.
				</p>
				<ul v-else class="space-y-1">
					<li
						v-for="row in insights.declared"
						:key="row.name"
						class="flex items-start justify-between gap-2 text-[13px]"
					>
						<span>
							<b>{{ row.value }}</b>
							<span class="text-on-surface-variant"> · {{ row.category }}</span>
							<span
								v-if="row.priority !== 'Normal'"
								class="ml-1 rounded px-1.5 py-0.5 text-[10px] font-semibold"
								:class="
									row.priority === 'Required'
										? 'bg-error-container text-on-error-container'
										: 'bg-secondary-container text-on-secondary-container'
								"
								>{{ row.priority }}</span
							>
							<span
								v-if="row.sensitive"
								class="ml-1 rounded bg-surface-container-high px-1.5 py-0.5 text-[10px]"
								>Sensitive</span
							>
							<span
								v-if="row.guest_profile !== insights.guest_profile"
								class="block text-[11px] text-on-surface-variant"
								>{{ row.guest_name }}</span
							>
						</span>
						<button
							v-if="insights.can_edit && editable"
							type="button"
							class="text-[11px] text-on-surface-variant hover:text-error"
							:disabled="busy"
							:title="`The guest no longer wants ${row.value}`"
							@click="retire(row)"
						>
							Remove
						</button>
					</li>
				</ul>
			</div>

			<!-- This stay's own requests -->
			<div class="space-y-1.5">
				<p class="text-[12px] font-semibold text-on-surface">This stay</p>
				<p v-if="!insights.requests.length" class="text-[12px] text-on-surface-variant">
					No requests for this stay.
				</p>
				<ul v-else class="space-y-1.5">
					<li
						v-for="row in insights.requests"
						:key="row.name"
						class="flex flex-wrap items-center justify-between gap-2 text-[13px]"
					>
						<span>
							<b>{{ row.value }}</b>
							<span class="text-on-surface-variant"> · {{ row.category }}</span>
							<span
								v-if="row.priority !== 'Normal'"
								class="ml-1 text-[11px] font-semibold"
								>{{ row.priority }}</span
							>
							<span
								v-if="row.source === 'Applied suggestion'"
								class="block text-[11px] text-on-surface-variant"
								>From a suggestion</span
							>
						</span>
						<span v-if="insights.can_edit && editable" class="flex gap-2 text-[11px]">
							<button
								type="button"
								class="font-semibold text-primary"
								:disabled="busy"
								@click="run(() => closeStayRequestApi(row.name, 'Done'))"
							>
								Done
							</button>
							<button
								type="button"
								class="text-on-surface-variant"
								:disabled="busy"
								@click="run(() => copyRequestToProfileApi(row.name))"
							>
								Keep for every stay
							</button>
							<button
								type="button"
								class="text-on-surface-variant hover:text-error"
								:disabled="busy"
								@click="run(() => closeStayRequestApi(row.name, 'Cancelled'))"
							>
								Cancel
							</button>
						</span>
					</li>
				</ul>
			</div>

			<!-- Observed: from completed history, never applied on its own -->
			<div v-if="insights.suggestions_enabled" class="space-y-1.5">
				<p class="text-[12px] font-semibold text-on-surface">From past visits</p>
				<p v-if="insights.no_history" class="text-[12px] text-on-surface-variant">
					No history yet.
				</p>
				<p
					v-else-if="!insights.suggestions.length"
					class="text-[12px] text-on-surface-variant"
				>
					Nothing has happened {{ insights.min_occurrences }} times or more yet.
				</p>
				<ul v-else class="space-y-2">
					<li
						v-for="item in insights.suggestions"
						:key="item.key"
						class="rounded-lg border border-dashed border-outline-variant px-3 py-2"
					>
						<p class="text-[13px]">
							<b>{{ item.title }}</b>
							<span class="text-on-surface-variant"> · {{ item.type }}</span>
						</p>
						<p class="text-[12px] text-on-surface-variant">
							{{ item.evidence }}
							<span v-if="item.dismissed">
								· dismissed
								{{
									item.dismissed === 1 ? "once" : `${item.dismissed} times`
								}}</span
							>
						</p>
						<div
							v-if="insights.can_edit && editable"
							class="mt-1.5 flex flex-wrap gap-3 text-[12px]"
						>
							<span v-if="item.applied_to_stay" class="text-on-surface-variant"
								>Applied to this stay</span
							>
							<button
								v-else
								type="button"
								class="font-semibold text-primary"
								:disabled="busy"
								@click="
									run(() => applySuggestionApi(stayId, item.key, item.evidence))
								"
							>
								Use for this stay
							</button>
							<button
								type="button"
								class="font-semibold text-primary"
								:disabled="busy"
								@click="
									run(() =>
										saveSuggestionApi(
											insights.guest_profile,
											item.key,
											item.evidence,
											stayId
										)
									)
								"
							>
								Save to profile
							</button>
							<button
								type="button"
								class="text-on-surface-variant"
								:disabled="busy"
								@click="
									run(() =>
										dismissSuggestionApi(
											insights.guest_profile,
											item.key,
											item.evidence,
											stayId
										)
									)
								"
							>
								Dismiss
							</button>
						</div>
					</li>
				</ul>
			</div>

			<!-- Add a preference or a request -->
			<form
				v-if="form.open"
				class="space-y-2 rounded-lg bg-surface-container-low p-3"
				@submit.prevent="save"
			>
				<div class="flex gap-3 text-[12px]">
					<label class="flex items-center gap-1">
						<input v-model="form.scope" type="radio" value="stay" /> This stay
					</label>
					<label class="flex items-center gap-1">
						<input v-model="form.scope" type="radio" value="profile" /> Every stay
					</label>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<label class="text-[12px] text-on-surface-variant">
						Category
						<select
							v-model="form.category"
							class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
						>
							<option v-for="category in options.categories" :key="category">
								{{ category }}
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Priority
						<select
							v-model="form.priority"
							class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
						>
							<option
								v-for="priority in options.priorities"
								:key="priority"
								:disabled="priority === 'Required' && !isRoomCategory"
							>
								{{ priority }}
							</option>
						</select>
					</label>
				</div>
				<label v-if="isRoomCategory" class="block text-[12px] text-on-surface-variant">
					Room feature
					<select
						v-model="form.roomFeature"
						class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
					>
						<option value="">
							{{
								form.category === "Floor"
									? "None: write the floor below"
									: "Pick one"
							}}
						</option>
						<option
							v-for="feature in featuresForCategory"
							:key="feature.name"
							:value="feature.name"
						>
							{{ feature.name }}
						</option>
					</select>
				</label>
				<label class="block text-[12px] text-on-surface-variant">
					In the guest's words
					<input
						v-model="form.value"
						type="text"
						:placeholder="valuePlaceholder"
						class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
					/>
				</label>
				<div v-if="form.scope === 'profile'" class="flex flex-wrap gap-4 text-[12px]">
					<label v-if="insights.can_see_sensitive" class="flex items-center gap-1">
						<input v-model="form.sensitive" type="checkbox" /> Sensitive (medical,
						accessibility, religious)
					</label>
					<label class="flex items-center gap-1">
						<input v-model="form.thisPropertyOnly" type="checkbox" /> This hotel only
					</label>
				</div>
				<div class="flex justify-end gap-2">
					<button
						type="button"
						class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold"
						@click="form.open = false"
					>
						Cancel
					</button>
					<button
						type="submit"
						class="rounded-lg bg-primary px-3 py-1.5 text-[12px] font-semibold text-on-primary disabled:opacity-50"
						:disabled="busy || !canSave"
					>
						Save
					</button>
				</div>
			</form>
		</template>
	</section>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import {
	addGuestPreferenceApi,
	addStayRequestApi,
	applySuggestionApi,
	closeStayRequestApi,
	copyRequestToProfileApi,
	dismissSuggestionApi,
	fetchGuestInsightsApi,
	fetchPreferenceOptionsApi,
	hotelErrorMessage,
	retireGuestPreferenceApi,
	saveSuggestionApi,
} from "@/api/hotel.api";

// One stay's lead guest: declared preferences first, then this stay's requests, then what their
// history suggests. `editable` is false once the stay is over.
const props = defineProps({
	stayId: { type: String, required: true },
	editable: { type: Boolean, default: true },
});
// After a preference or request changed, so the ranked rooms can be fetched again.
const emit = defineEmits(["changed"]);

const insights = ref(null);
const options = ref({ categories: [], room_categories: [], priorities: [], room_features: [] });
const loading = ref(false);
const busy = ref(false);
const error = ref("");

const blankForm = () => ({
	open: false,
	scope: "stay",
	category: "Noise",
	priority: "Normal",
	roomFeature: "",
	value: "",
	sensitive: false,
	thisPropertyOnly: false,
});
const form = reactive(blankForm());

const isRoomCategory = computed(() => options.value.room_categories.includes(form.category));
// Features of the matching category first; any feature can still be picked.
const featuresForCategory = computed(() => {
	const all = options.value.room_features || [];
	const same = all.filter((feature) => feature.category === form.category);
	return same.length ? same : all;
});
const valuePlaceholder = computed(() =>
	form.category === "Floor" ? "High floor, Low floor, or Floor 4" : "Quiet room, twin beds…"
);
const canSave = computed(() => {
	if (!form.value.trim() && !form.roomFeature) return false;
	if (isRoomCategory.value && form.category !== "Floor" && form.category !== "Room") {
		return !!form.roomFeature;
	}
	return true;
});

watch(
	() => form.category,
	() => {
		form.roomFeature = "";
		if (!isRoomCategory.value && form.priority === "Required") form.priority = "Normal";
	}
);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		insights.value = await fetchGuestInsightsApi(props.stayId);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function openForm() {
	if (!options.value.categories.length) {
		try {
			options.value = await fetchPreferenceOptionsApi();
		} catch (e) {
			error.value = hotelErrorMessage(e);
			return;
		}
	}
	Object.assign(form, blankForm(), { open: true });
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		insights.value = await command();
		emit("changed");
		return true;
	} catch (e) {
		error.value = hotelErrorMessage(e);
		return false;
	} finally {
		busy.value = false;
	}
}

async function save() {
	const fields = { ...form };
	const saved = await run(() =>
		form.scope === "stay"
			? addStayRequestApi(props.stayId, fields)
			: addGuestPreferenceApi(insights.value.guest_profile, props.stayId, fields)
	);
	if (saved) form.open = false;
}

function retire(row) {
	run(() => retireGuestPreferenceApi(row.name, props.stayId));
}

watch(() => props.stayId, load, { immediate: true });

defineExpose({ reload: load });
</script>
