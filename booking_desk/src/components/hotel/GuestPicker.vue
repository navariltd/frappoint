<template>
	<div class="space-y-3">
		<div
			v-if="modelValue"
			class="flex items-center justify-between rounded-lg border border-secondary bg-secondary-container/40 px-4 py-3"
		>
			<div>
				<p class="text-[14px] font-semibold text-on-surface">{{ modelValue.full_name }}</p>
				<p class="text-[12px] text-on-surface-variant">
					{{
						[modelValue.email, modelValue.mobile_no].filter(Boolean).join(" · ") ||
						modelValue.name
					}}
				</p>
			</div>
			<button type="button" class="text-[12px] font-semibold text-primary" @click="clear">
				Change
			</button>
		</div>

		<template v-else-if="!creating">
			<div class="relative">
				<span
					class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
					>search</span
				>
				<input
					v-model="query"
					type="search"
					class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest pl-10 pr-3 py-2 text-[13px]"
					placeholder="Search guests by name, phone or email"
					@input="onSearch"
				/>
			</div>
			<p v-if="error" class="text-[12px] text-error">{{ error }}</p>
			<ul
				v-if="results.length"
				class="divide-y divide-outline-variant rounded-lg border border-outline-variant bg-surface-container-lowest"
			>
				<li v-for="guest in results" :key="guest.name">
					<button
						type="button"
						class="w-full text-left px-4 py-2.5 hover:bg-surface-container flex items-center justify-between gap-3"
						@click="choose(guest)"
					>
						<span>
							<span class="text-[13px] font-semibold text-on-surface">{{
								guest.full_name
							}}</span>
							<span class="block text-[11px] text-on-surface-variant">
								{{ [guest.email, guest.mobile_no].filter(Boolean).join(" · ") }}
							</span>
						</span>
						<span class="flex items-center gap-2">
							<span
								v-if="guest.restriction_flag"
								class="text-[10px] font-bold uppercase text-error"
								>Do not rent</span
							>
							<span
								v-if="guest.vip_level"
								class="text-[10px] font-bold text-secondary-ink"
								>{{ guest.vip_level }}</span
							>
							<span class="text-[10px] text-on-surface-variant">{{
								guest.match
							}}</span>
						</span>
					</button>
				</li>
			</ul>
			<p v-else-if="searched && !searching" class="text-[12px] text-on-surface-variant">
				No guest found.
			</p>
			<button
				type="button"
				class="text-[12px] font-semibold text-primary"
				@click="startCreate"
			>
				+ New guest
			</button>
		</template>

		<form v-else class="space-y-3" @submit.prevent="create(false)">
			<div class="grid grid-cols-2 gap-3">
				<label class="text-[12px] text-on-surface-variant">
					First name
					<input v-model="draft.first_name" required class="hotel-input" />
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Last name
					<input v-model="draft.last_name" class="hotel-input" />
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Email
					<input v-model="draft.email" type="email" class="hotel-input" />
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Mobile
					<input v-model="draft.mobile_no" type="tel" class="hotel-input" />
				</label>
			</div>
			<p v-if="error" class="text-[12px] text-error">{{ error }}</p>

			<div
				v-if="matches.length"
				class="rounded-lg border border-tertiary bg-tertiary-container/30 p-3 space-y-2"
			>
				<p class="text-[12px] font-semibold text-on-surface">
					These guests already have this email or phone. Use one of them?
				</p>
				<button
					v-for="guest in matches"
					:key="guest.name"
					type="button"
					class="block text-[12px] font-semibold text-primary"
					@click="choose(guest)"
				>
					{{ guest.full_name }} ({{ guest.match }})
				</button>
				<button
					type="button"
					class="text-[12px] text-on-surface-variant underline"
					@click="create(true)"
				>
					No, create a new guest anyway
				</button>
			</div>

			<div class="flex gap-2">
				<button
					type="submit"
					class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[12px] font-semibold disabled:opacity-50"
					:disabled="saving"
				>
					Create guest
				</button>
				<button
					type="button"
					class="px-3 py-2 text-[12px] text-on-surface-variant"
					@click="cancelCreate"
				>
					Back to search
				</button>
			</div>
		</form>
	</div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { createGuestApi, hotelErrorMessage, searchGuestsApi } from "@/api/hotel.api";

defineProps({ modelValue: { type: Object, default: null } });
const emit = defineEmits(["update:modelValue"]);

const query = ref("");
const results = ref([]);
const searching = ref(false);
const searched = ref(false);
const creating = ref(false);
const saving = ref(false);
const error = ref("");
const matches = ref([]);
const draft = reactive({ first_name: "", last_name: "", email: "", mobile_no: "" });

let timer = null;
let lastRequest = 0;

function onSearch() {
	clearTimeout(timer);
	timer = setTimeout(runSearch, 300);
}

async function runSearch() {
	const text = query.value.trim();
	error.value = "";
	if (text.length < 2) {
		results.value = [];
		searched.value = false;
		return;
	}
	const request = ++lastRequest;
	searching.value = true;
	try {
		const rows = await searchGuestsApi(text);
		if (request === lastRequest) results.value = rows || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		searching.value = false;
		searched.value = true;
	}
}

function choose(guest) {
	if (guest.restriction_flag) {
		error.value = `${guest.full_name} is marked Do Not Rent and can't be booked.`;
		return;
	}
	emit("update:modelValue", guest);
	creating.value = false;
	matches.value = [];
}

function clear() {
	emit("update:modelValue", null);
}

function startCreate() {
	creating.value = true;
	error.value = "";
	const words = query.value.trim().split(/\s+/);
	if (!query.value.includes("@") && !/\d{4}/.test(query.value)) {
		draft.first_name = words[0] || "";
		draft.last_name = words.slice(1).join(" ");
	}
}

function cancelCreate() {
	creating.value = false;
	matches.value = [];
	error.value = "";
}

async function create(force) {
	saving.value = true;
	error.value = "";
	try {
		const result = await createGuestApi({ ...draft, force: force ? 1 : 0 });
		if (result?.created) {
			choose({
				name: result.guest,
				full_name: result.full_name,
				email: draft.email,
				mobile_no: draft.mobile_no,
			});
		} else {
			matches.value = result?.matches || [];
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		saving.value = false;
	}
}
</script>

<style scoped>
.hotel-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
