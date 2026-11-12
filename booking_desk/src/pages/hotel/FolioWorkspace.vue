<template>
	<div class="px-6 py-5 space-y-5 max-w-6xl">
		<div class="flex gap-4 text-[12px] font-semibold">
			<RouterLink
				:to="{ name: 'HotelStay', params: { stayId: route.params.stayId } }"
				class="text-primary"
				>← Reservation {{ route.params.stayId }}</RouterLink
			>
			<RouterLink :to="{ name: 'FrontDeskToday' }" class="text-primary"
				>Front Desk</RouterLink
			>
		</div>

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
					<div class="flex items-center gap-3">
						<h1 class="text-[22px] font-semibold text-on-surface">
							Folios · {{ data.stay.lead_guest_name }}
						</h1>
						<HotelStatusBadge :status="data.stay.status" />
					</div>
					<p class="text-[13px] text-on-surface-variant">
						{{ data.stay.name }} · Business date
						{{ formatNight(data.business_date) }}
					</p>
				</div>
				<div class="flex gap-3">
					<div
						class="rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-2 text-right"
					>
						<p class="text-[11px] text-on-surface-variant">Balance</p>
						<p class="text-[18px] font-semibold">
							{{ money(data.totals.balance) }}
						</p>
					</div>
					<div
						class="rounded-xl border border-dashed border-outline-variant px-4 py-2 text-right"
						title="Nights not posted yet. Night audit posts them; they are not part of the balance."
					>
						<p class="text-[11px] text-on-surface-variant">Pending, not in balance</p>
						<p class="text-[18px] font-semibold text-on-surface-variant">
							{{ money(data.totals.pending) }}
						</p>
					</div>
				</div>
			</header>

			<p v-if="!data.folios.length" class="text-[13px] text-on-surface-variant">
				This stay has no folio yet. It gets one when it is confirmed.
			</p>

			<!-- Post a charge -->
			<section
				v-if="data.actions.can_post && postableFolios.length"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<h2 class="text-[15px] font-semibold">Post a charge</h2>
				<div class="grid gap-3 md:grid-cols-[2fr_1fr]">
					<div class="space-y-2">
						<div
							v-if="form.item"
							class="flex items-center justify-between rounded-lg border border-secondary bg-secondary-container/40 px-3 py-2"
						>
							<span>
								<span class="text-[13px] font-semibold">{{
									form.item.item_name
								}}</span>
								<span class="block text-[11px] text-on-surface-variant">
									{{ form.item.name }} · {{ form.item.item_group }}
									<template v-if="form.chargeCode">
										· posts as {{ form.chargeCode }}</template
									>
								</span>
							</span>
							<button
								type="button"
								class="text-[12px] font-semibold text-primary"
								@click="clearItem"
							>
								Change
							</button>
						</div>
						<template v-else>
							<input
								v-model="itemQuery"
								type="search"
								class="folio-input"
								placeholder="Search items: massage, breakfast, laundry…"
								@input="onItemSearch"
							/>
							<ul
								v-if="itemResults.length"
								class="max-h-56 overflow-y-auto divide-y divide-outline-variant rounded-lg border border-outline-variant"
							>
								<li v-for="item in itemResults" :key="item.name">
									<button
										type="button"
										class="w-full text-left px-3 py-2 hover:bg-surface-container"
										@click="chooseItem(item)"
									>
										<span class="text-[13px] font-semibold">{{
											item.item_name
										}}</span>
										<span class="block text-[11px] text-on-surface-variant">
											{{ item.name }} · {{ item.item_group }}
										</span>
									</button>
								</li>
							</ul>
							<p
								v-else-if="itemSearched"
								class="text-[12px] text-on-surface-variant"
							>
								No postable item found. Items need a charge code that covers their
								Item Group.
							</p>
						</template>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<label class="text-[12px] text-on-surface-variant">
							Quantity
							<input
								v-model.number="form.quantity"
								type="number"
								min="1"
								step="1"
								class="folio-input"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Rate
							<input
								v-model.number="form.rate"
								type="number"
								min="0"
								step="0.01"
								class="folio-input"
							/>
						</label>
					</div>
				</div>
				<div class="grid gap-3 md:grid-cols-3">
					<label
						v-if="postableFolios.length > 1"
						class="text-[12px] text-on-surface-variant"
					>
						Folio
						<select v-model="form.folio" class="folio-input">
							<option
								v-for="entry in postableFolios"
								:key="entry.folio.name"
								:value="entry.folio.name"
							>
								{{ entry.folio.folio_label }} · {{ entry.folio.payee_name }}
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Consumed by
						<select v-model="form.stayGuest" class="folio-input">
							<option :value="null">Not recorded</option>
							<option
								v-for="guest in data.guests"
								:key="guest.name"
								:value="guest.name"
							>
								{{ guest.guest_name }} ({{ guest.role }})
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Notes
						<input v-model="form.notes" class="folio-input" />
					</label>
				</div>
				<div class="flex items-center justify-between">
					<p class="text-[13px]">
						Total <b>{{ money(formTotal) }}</b>
					</p>
					<button
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy || !form.item || !(form.quantity > 0) || !(form.rate > 0)"
						@click="postCharge"
					>
						Post charge
					</button>
				</div>
			</section>

			<!-- Folios -->
			<section
				v-for="entry in data.folios"
				:key="entry.folio.name"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<div class="flex items-center gap-3">
							<h2 class="text-[15px] font-semibold">
								{{ entry.folio.folio_label }}
							</h2>
							<HotelStatusBadge :status="entry.folio.status" />
						</div>
						<p class="text-[12px] text-on-surface-variant">
							{{ entry.folio.name }} · Payee
							{{ entry.folio.payee_name || "not set yet" }}
						</p>
					</div>
					<div class="text-right">
						<p class="text-[11px] text-on-surface-variant">Balance</p>
						<p class="text-[16px] font-semibold">{{ money(entry.folio.balance) }}</p>
						<button
							v-if="data.actions.can_rebuild"
							type="button"
							class="text-[11px] font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							title="Recompute the balance from the posted lines"
							@click="rebuild(entry.folio.name)"
						>
							Check balance
						</button>
					</div>
				</div>

				<p v-if="!entry.transactions.length" class="text-[13px] text-on-surface-variant">
					Nothing posted yet.
				</p>
				<div v-else class="overflow-x-auto">
					<table class="w-full text-[12px]">
						<thead class="text-left text-on-surface-variant">
							<tr class="border-b border-outline-variant">
								<th class="py-1.5 font-semibold">Date</th>
								<th class="py-1.5 font-semibold">Description</th>
								<th class="py-1.5 font-semibold">Guest</th>
								<th class="py-1.5 font-semibold">Room</th>
								<th class="py-1.5 text-right font-semibold">Charges</th>
								<th class="py-1.5 text-right font-semibold">Credits</th>
								<th class="py-1.5"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="line in entry.transactions"
								:key="line.name"
								class="border-b border-outline-variant align-top"
								:class="{ 'text-on-surface-variant': line.reversed_by }"
							>
								<td class="py-1.5 whitespace-nowrap">
									{{ formatNight(line.service_date) }}
								</td>
								<td class="py-1.5">
									<span :class="{ 'line-through': line.reversed_by }">{{
										line.description_snapshot
									}}</span>
									<span v-if="line.quantity > 1" class="text-on-surface-variant">
										× {{ line.quantity }}</span
									>
									<span class="block text-[11px] text-on-surface-variant">
										{{ line.charge_code }}
										<template v-if="line.reversed_by"> · reversed</template>
										<template v-if="line.reason">
											· {{ line.reason }}</template
										>
									</span>
								</td>
								<td class="py-1.5">{{ line.consumer_name || "" }}</td>
								<td class="py-1.5">{{ line.room_number_snapshot || "" }}</td>
								<td class="py-1.5 text-right whitespace-nowrap">
									<template v-if="line.direction === 'Debit'">{{
										money(line.gross_amount)
									}}</template>
								</td>
								<td class="py-1.5 text-right whitespace-nowrap">
									<template v-if="line.direction === 'Credit'">{{
										money(line.gross_amount)
									}}</template>
								</td>
								<td class="py-1.5 pl-3 text-right">
									<button
										v-if="canReverse(entry.folio, line)"
										type="button"
										class="text-[11px] font-semibold text-error disabled:opacity-50"
										:disabled="busy"
										@click="reverse(line)"
									>
										Reverse
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<section
				v-if="data.pending_nights.length"
				class="rounded-xl border border-dashed border-outline-variant p-4"
			>
				<h2 class="text-[15px] font-semibold">Pending nights</h2>
				<p class="text-[12px] text-on-surface-variant">
					Night audit posts each night to the folio. Until then they are estimates and
					not part of the balance.
				</p>
				<table class="mt-2 w-full text-[12px]">
					<tbody>
						<tr
							v-for="night in data.pending_nights"
							:key="night.night_date"
							class="border-b border-outline-variant"
						>
							<td class="py-1.5">{{ formatNight(night.night_date) }}</td>
							<td class="py-1.5 text-right">{{ money(night.total) }}</td>
						</tr>
					</tbody>
				</table>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
	fetchFolioItemRateApi,
	fetchStayFoliosApi,
	hotelErrorMessage,
	postFolioChargeApi,
	rebuildFolioBalanceApi,
	reverseFolioTransactionApi,
	searchFolioItemsApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

const POSTABLE = ["Open", "Post-Stay Open"];

const route = useRoute();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");

const itemQuery = ref("");
const itemResults = ref([]);
const itemSearched = ref(false);
const form = reactive(emptyForm());

const postableFolios = computed(() =>
	(data.value?.folios || []).filter((entry) => POSTABLE.includes(entry.folio.status))
);
const formTotal = computed(() => (Number(form.quantity) || 0) * (Number(form.rate) || 0));

function newRequestId() {
	return window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyForm(folio = null) {
	// One request id per charge: a retry of the same charge posts once.
	return {
		folio,
		item: null,
		chargeCode: null,
		quantity: 1,
		rate: null,
		stayGuest: null,
		notes: "",
		requestId: newRequestId(),
	};
}

function resetForm() {
	const folio =
		postableFolios.value.find((entry) => entry.folio.is_default)?.folio.name ||
		postableFolios.value[0]?.folio.name ||
		null;
	Object.assign(form, emptyForm(folio));
	itemQuery.value = "";
	itemResults.value = [];
	itemSearched.value = false;
}

function money(amount) {
	return formatMoney(amount, data.value?.stay?.currency);
}

function canReverse(folio, line) {
	return (
		data.value.actions.can_reverse &&
		POSTABLE.includes(folio.status) &&
		!line.reverses &&
		!line.reversed_by
	);
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await fetchStayFoliosApi(route.params.stayId);
		if (!form.folio || !postableFolios.value.some((e) => e.folio.name === form.folio)) {
			resetForm();
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

let searchTimer = null;
let lastSearch = 0;

function onItemSearch() {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(searchItems, 300);
}

async function searchItems() {
	const request = ++lastSearch;
	try {
		const rows = await searchFolioItemsApi(form.folio, itemQuery.value.trim());
		if (request === lastSearch) {
			itemResults.value = rows || [];
			itemSearched.value = true;
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	}
}

async function chooseItem(item) {
	form.item = item;
	itemResults.value = [];
	try {
		const details = await fetchFolioItemRateApi(form.folio, item.name);
		form.chargeCode = details?.charge_code || null;
		form.rate = details?.rate || null;
	} catch (e) {
		form.item = null;
		error.value = hotelErrorMessage(e);
	}
}

function clearItem() {
	form.item = null;
	form.chargeCode = null;
	form.rate = null;
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		await command();
		await load();
		return true;
	} catch (e) {
		const message = hotelErrorMessage(e);
		// Reload first: loading clears the error, and the message must stay on screen.
		await load();
		error.value = message;
		return false;
	} finally {
		busy.value = false;
	}
}

async function postCharge() {
	const posted = await run(() =>
		postFolioChargeApi({
			folio: form.folio,
			item: form.item.name,
			quantity: form.quantity,
			rate: form.rate,
			stayGuest: form.stayGuest,
			notes: form.notes,
			requestId: form.requestId,
		})
	);
	// After a failure the same request id is kept, so trying again can't post twice.
	if (posted) resetForm();
}

async function reverse(line) {
	const answer = await ask({
		tone: "danger",
		title: `Reverse "${line.description_snapshot}" (${money(line.gross_amount)})?`,
		message: "A reversing line is posted. The original line stays on the folio.",
		reasonLabel: "Reason for the reversal",
		confirmLabel: "Reverse",
	});
	if (answer) run(() => reverseFolioTransactionApi(line.name, answer.reason));
}

async function rebuild(folio) {
	let result = null;
	const checked = await run(async () => {
		result = await rebuildFolioBalanceApi(folio);
	});
	if (!checked || !result) return;
	notify(
		result.drift
			? {
					tone: "warning",
					title: "The folio balance was corrected",
					message: `It showed ${money(
						result.before.balance
					)}. It now matches the posted lines: ${money(result.after.balance)}.`,
			  }
			: {
					title: "The balance matches the posted lines",
					message: `${folio}: ${money(result.after.balance)}.`,
			  }
	);
}

onMounted(load);
watch(() => route.params.stayId, load);
</script>

<style scoped>
.folio-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
