<template>
	<div class="px-6 py-5 max-w-[1600px]">
		<HotelUnavailable v-if="blocked" :message="blocked" />
		<div
			v-else
			class="grid gap-5 lg:grid-cols-[minmax(300px,380px)_minmax(0,1fr)] lg:items-start"
		>
			<!-- Accounts list. On small screens it gives way to the selected account. -->
			<section
				class="space-y-3 lg:sticky lg:top-4"
				:class="{ 'hidden lg:block': selectedId || creating }"
				aria-label="House accounts"
			>
				<div class="flex items-center gap-2">
					<label class="relative block flex-1">
						<span
							class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
							aria-hidden="true"
							>search</span
						>
						<input
							v-model="search"
							type="search"
							class="w-full rounded-lg border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-[13px] text-on-surface"
							placeholder="Search accounts"
							aria-label="Search house accounts"
						/>
					</label>
					<button
						v-if="data?.can_manage"
						type="button"
						class="shrink-0 rounded-lg bg-primary text-on-primary px-3 py-2 text-[13px] font-semibold"
						@click="startCreate"
					>
						New account
					</button>
				</div>
				<div class="flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
					<button
						v-for="option in FILTERS"
						:key="option.key"
						type="button"
						class="rounded-full border px-3 py-1 text-[12px] font-semibold"
						:class="
							filter === option.key
								? 'border-primary bg-primary text-on-primary'
								: 'border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container'
						"
						:aria-pressed="filter === option.key"
						@click="filter = option.key"
					>
						{{ option.label }}
						<span class="ml-1 opacity-80">{{ counts[option.key] }}</span>
					</button>
				</div>

				<p
					v-if="error"
					class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] text-on-surface"
				>
					{{ error }}
				</p>
				<p v-else-if="loading && !data" class="text-[13px] text-on-surface-variant">
					Loading…
				</p>
				<p
					v-else-if="data && !data.accounts.length"
					class="text-[13px] text-on-surface-variant"
				>
					No house accounts yet. Open one for staff meals, an event, or visitors who
					aren't staying.
				</p>
				<p v-else-if="data && !visible.length" class="text-[13px] text-on-surface-variant">
					No accounts match.
				</p>

				<ul
					v-else-if="data"
					class="divide-y divide-outline-variant overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest lg:max-h-[calc(100vh-14rem)] lg:overflow-y-auto"
				>
					<li v-for="account in visible" :key="account.name">
						<RouterLink
							:to="{
								name: 'HotelHouseAccountFolios',
								params: { accountId: account.name },
							}"
							class="block border-l-[3px] px-4 py-3 transition-colors"
							:class="
								account.name === selectedId
									? 'border-l-primary bg-primary/5'
									: 'border-l-transparent hover:bg-surface-container'
							"
							:aria-current="account.name === selectedId ? 'page' : undefined"
						>
							<span class="flex items-start justify-between gap-3">
								<span class="min-w-0">
									<span
										class="block truncate text-[14px] font-semibold text-on-surface"
										>{{ account.account_name }}</span
									>
									<span class="block text-[12px] text-on-surface-variant">
										{{ account.account_type }}
										<template v-if="account.valid_from || account.valid_to">
											· {{ formatNight(account.valid_from) }} →
											{{ formatNight(account.valid_to) }}
										</template>
									</span>
								</span>
								<span class="shrink-0 text-right">
									<span
										class="block text-[14px] font-semibold text-on-surface"
										>{{ formatMoney(account.balance, account.currency) }}</span
									>
									<span class="block text-[11px]" :class="folioTone(account)">{{
										folioLabel(account)
									}}</span>
								</span>
							</span>
							<span class="mt-1 flex items-center justify-between gap-3">
								<span class="truncate text-[12px] text-on-surface-variant"
									>Bills {{ account.payee_name || "the walk-in Customer" }}</span
								>
								<HotelStatusBadge
									v-if="account.status !== 'Active'"
									:status="account.status"
								/>
							</span>
						</RouterLink>
					</li>
				</ul>
			</section>

			<!-- New account -->
			<section v-if="creating" class="min-w-0 space-y-3" aria-label="New house account">
				<form
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 space-y-4"
					@submit.prevent="create"
				>
					<div>
						<h2 class="text-[18px] font-semibold text-on-surface">
							New house account
						</h2>
						<p class="text-[12px] text-on-surface-variant">
							Charges post to its folio like a stay's, but it has no room and never
							counts in occupancy.
						</p>
					</div>
					<ActionBanner
						:banner="banner"
						:busy="busy"
						@confirm="confirmBanner"
						@cancel="cancelBanner"
					/>
					<div class="grid gap-3 md:grid-cols-2">
						<label class="text-[12px] text-on-surface-variant">
							Name
							<input
								v-model="form.accountName"
								required
								class="account-input"
								placeholder="Staff Meals, Leadership Summit…"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Bill to (Customer ID, optional)
							<input
								v-model="form.payeeCustomer"
								class="account-input"
								placeholder="The walk-in Customer if empty"
							/>
						</label>
					</div>
					<fieldset class="space-y-2">
						<legend class="text-[12px] text-on-surface-variant">Type</legend>
						<div class="grid gap-2 md:grid-cols-2">
							<label
								v-for="type in TYPES"
								:key="type.value"
								class="flex cursor-pointer gap-3 rounded-lg border p-3"
								:class="
									form.accountType === type.value
										? 'border-primary bg-primary/5'
										: 'border-outline-variant'
								"
							>
								<input
									v-model="form.accountType"
									type="radio"
									:value="type.value"
									class="mt-0.5"
								/>
								<span>
									<span
										class="block text-[13px] font-semibold text-on-surface"
										>{{ type.label }}</span
									>
									<span class="block text-[12px] text-on-surface-variant">{{
										type.hint
									}}</span>
								</span>
							</label>
						</div>
					</fieldset>
					<div v-if="form.accountType === 'Event'" class="grid gap-3 md:grid-cols-2">
						<label class="text-[12px] text-on-surface-variant">
							From
							<input v-model="form.validFrom" type="date" class="account-input" />
						</label>
						<label class="text-[12px] text-on-surface-variant">
							To
							<input v-model="form.validTo" type="date" class="account-input" />
						</label>
					</div>
					<div class="flex justify-end gap-2">
						<button
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
							@click="cancelCreate"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="busy || !form.accountName.trim()"
						>
							Open account
						</button>
					</div>
				</form>
			</section>

			<!-- The selected account: its details, then its folios -->
			<section
				v-else-if="selectedId"
				class="min-w-0 space-y-3"
				aria-label="Selected account"
			>
				<RouterLink
					:to="{ name: 'HotelHouseAccounts' }"
					class="text-[12px] font-semibold text-primary lg:hidden"
				>
					← All house accounts
				</RouterLink>
				<ActionBanner
					:banner="banner"
					:busy="busy"
					@confirm="confirmBanner"
					@cancel="cancelBanner"
				/>
				<div
					v-if="selected"
					class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest px-5 py-3"
				>
					<p class="text-[12px] text-on-surface-variant">
						<span class="font-semibold text-on-surface">{{
							selected.account_type
						}}</span>
						account · bills
						<span class="font-semibold text-on-surface">{{
							selected.payee_name || "the walk-in Customer"
						}}</span>
						<template v-if="selected.valid_from || selected.valid_to">
							· open {{ formatNight(selected.valid_from) }} →
							{{ formatNight(selected.valid_to) }}
						</template>
					</p>
					<div class="flex items-center gap-3">
						<a
							:href="`/app/house-account/${encodeURIComponent(selected.name)}`"
							target="_blank"
							class="text-[12px] text-on-surface-variant"
							>Open in desk</a
						>
						<button
							v-if="data?.can_manage && selected.status === 'Active'"
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold text-on-surface disabled:opacity-50"
							:disabled="busy"
							@click="close(selected)"
						>
							Close account
						</button>
					</div>
				</div>
				<div
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-5"
				>
					<FolioWorkspace :key="selectedId" embedded @changed="load" />
				</div>
			</section>

			<section
				v-else
				class="hidden min-h-[320px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-outline-variant text-center lg:flex"
			>
				<span
					class="material-symbols-outlined text-[36px] text-on-surface-variant"
					aria-hidden="true"
					>storefront</span
				>
				<p class="text-[14px] font-semibold text-on-surface">Select a house account</p>
				<p class="max-w-xs text-[12px] text-on-surface-variant">
					Its folio opens here: post charges, take payments and settle, next to the list.
				</p>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	closeHouseAccountApi,
	createHouseAccountApi,
	fetchHouseAccountsApi,
	hotelErrorMessage,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import FolioWorkspace from "@/pages/hotel/FolioWorkspace.vue";
import { useHotelStore } from "@/stores/hotel.store";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

const FILTERS = [
	{ key: "active", label: "Active", status: "Active" },
	{ key: "closed", label: "Closed", status: "Closed" },
	{ key: "all", label: "All", status: null },
];
const TYPES = [
	{
		value: "Permanent",
		label: "Permanent",
		hint: "Staff meals, a management account. Billed in periods.",
	},
	{
		value: "Event",
		label: "Event",
		hint: "A conference or wedding. Takes charges only between its dates.",
	},
];

const route = useRoute();
const router = useRouter();
const hotel = useHotelStore();
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const search = ref("");
const filter = ref("active");
const creating = ref(false);
const form = reactive(emptyForm());

const selectedId = computed(() => route.params.accountId || null);
const selected = computed(
	() => data.value?.accounts.find((account) => account.name === selectedId.value) || null
);
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

const matching = computed(() => {
	const text = search.value.trim().toLowerCase();
	const accounts = data.value?.accounts || [];
	if (!text) return accounts;
	return accounts.filter((account) =>
		[account.account_name, account.name, account.payee_name, account.account_type]
			.filter(Boolean)
			.some((value) => value.toLowerCase().includes(text))
	);
});
const counts = computed(() =>
	Object.fromEntries(
		FILTERS.map((option) => [
			option.key,
			option.status
				? matching.value.filter((account) => account.status === option.status).length
				: matching.value.length,
		])
	)
);
const visible = computed(() => {
	const status = FILTERS.find((option) => option.key === filter.value)?.status;
	return status ? matching.value.filter((account) => account.status === status) : matching.value;
});

/** What the balance in the list means: owed on the open folio, on account, or nothing. */
function folioLabel(account) {
	switch (account.folio_status) {
		case "Open":
		case "Post-Stay Open":
			return Number(account.balance) ? "owing" : "nothing owing";
		case "Transferred to AR":
			return "on account (AR)";
		case "Settlement Pending":
			return "invoice pending";
		case "Closed":
		case "Settled":
			return "settled";
		default:
			return "no folio yet";
	}
}

function folioTone(account) {
	if (account.folio_status === "Settlement Pending") return "font-semibold text-error";
	if (["Open", "Post-Stay Open"].includes(account.folio_status) && Number(account.balance))
		return "text-on-tertiary-container";
	return "text-on-surface-variant";
}

function emptyForm() {
	return {
		accountName: "",
		accountType: "Permanent",
		payeeCustomer: "",
		validFrom: "",
		validTo: "",
	};
}

function startCreate() {
	Object.assign(form, emptyForm());
	creating.value = true;
}

function cancelCreate() {
	creating.value = false;
}

async function load() {
	if (!hotel.property) return;
	loading.value = true;
	error.value = "";
	try {
		data.value = await fetchHouseAccountsApi(hotel.property);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		const result = await command();
		data.value = result;
		return result;
	} catch (e) {
		const message = hotelErrorMessage(e);
		await load();
		error.value = message;
		return null;
	} finally {
		busy.value = false;
	}
}

async function create() {
	const result = await run(() =>
		createHouseAccountApi({
			property: hotel.property,
			accountName: form.accountName.trim(),
			accountType: form.accountType,
			payeeCustomer: form.payeeCustomer.trim(),
			validFrom: form.accountType === "Event" ? form.validFrom : null,
			validTo: form.accountType === "Event" ? form.validTo : null,
		})
	);
	if (!result) return;
	creating.value = false;
	filter.value = "active";
	router.push({ name: "HotelHouseAccountFolios", params: { accountId: result.name } });
}

async function close(account) {
	const answer = await ask({
		tone: "danger",
		title: `Close ${account.account_name}?`,
		message: "Its folio must be settled first. A closed account takes no more charges.",
		reasonLabel: "Reason for closing",
		confirmLabel: "Close account",
	});
	if (answer) run(() => closeHouseAccountApi(account.name, answer.reason));
}

// Picking an account from the list leaves the new-account form.
watch(selectedId, () => (creating.value = false));

onMounted(async () => {
	await hotel.load();
	load();
});
watch(
	() => hotel.property,
	() => load()
);
</script>

<style scoped>
.account-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
