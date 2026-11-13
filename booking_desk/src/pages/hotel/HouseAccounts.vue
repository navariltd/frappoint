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
				<header class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<h1 class="text-[22px] font-semibold text-on-surface">House Accounts</h1>
						<p class="text-[13px] text-on-surface-variant">
							{{ hotel.currentProperty?.property_name }} · Folios with no room: staff
							meals, a conference, a visitor's restaurant bill. They never count in
							occupancy.
						</p>
					</div>
					<button
						v-if="data.can_manage && !form.open"
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold"
						@click="form.open = true"
					>
						New account
					</button>
				</header>

				<form
					v-if="form.open"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
					@submit.prevent="create"
				>
					<h2 class="text-[15px] font-semibold">New house account</h2>
					<div class="grid gap-3 md:grid-cols-3">
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
							Type
							<select v-model="form.accountType" class="account-input">
								<option value="Permanent">Permanent</option>
								<option value="Event">Event (with dates)</option>
							</select>
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
					<div v-if="form.accountType === 'Event'" class="grid gap-3 md:grid-cols-3">
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
							@click="resetForm"
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

				<p v-if="!data.accounts.length" class="text-[13px] text-on-surface-variant">
					No house accounts yet.
				</p>
				<ul
					v-else
					class="divide-y divide-outline-variant rounded-xl border border-outline-variant bg-surface-container-lowest"
				>
					<li
						v-for="account in data.accounts"
						:key="account.name"
						class="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
					>
						<div>
							<p class="text-[14px] font-semibold">
								{{ account.account_name }}
								<span class="text-[12px] font-normal text-on-surface-variant">
									· {{ account.account_type }}
									<template v-if="account.valid_from || account.valid_to">
										· {{ formatNight(account.valid_from) }} →
										{{ formatNight(account.valid_to) }}
									</template>
								</span>
							</p>
							<p class="text-[12px] text-on-surface-variant">
								{{ account.name }} · bills
								{{ account.payee_name || "the walk-in Customer" }}
								<template v-if="account.current_folio">
									· folio {{ account.current_folio }} ({{
										account.folio_status
									}})
								</template>
							</p>
						</div>
						<div class="flex items-center gap-3">
							<HotelStatusBadge :status="account.status" />
							<b class="text-[14px]">{{
								formatMoney(account.balance, account.currency)
							}}</b>
							<RouterLink
								:to="{
									name: 'HotelHouseAccountFolios',
									params: { accountId: account.name },
								}"
								class="text-[12px] font-semibold text-primary"
								>Open folio →</RouterLink
							>
							<button
								v-if="data.can_manage && account.status === 'Active'"
								type="button"
								class="text-[12px] font-semibold text-on-surface-variant disabled:opacity-50"
								:disabled="busy"
								@click="close(account)"
							>
								Close
							</button>
						</div>
					</li>
				</ul>
			</template>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
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
import { useHotelStore } from "@/stores/hotel.store";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

const hotel = useHotelStore();
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const form = reactive(emptyForm());

const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

function emptyForm() {
	return {
		open: false,
		accountName: "",
		accountType: "Permanent",
		payeeCustomer: "",
		validFrom: "",
		validTo: "",
	};
}

function resetForm() {
	Object.assign(form, emptyForm());
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
		data.value = await command();
		return true;
	} catch (e) {
		const message = hotelErrorMessage(e);
		await load();
		error.value = message;
		return false;
	} finally {
		busy.value = false;
	}
}

async function create() {
	const done = await run(() =>
		createHouseAccountApi({
			property: hotel.property,
			accountName: form.accountName.trim(),
			accountType: form.accountType,
			payeeCustomer: form.payeeCustomer.trim(),
			validFrom: form.accountType === "Event" ? form.validFrom : null,
			validTo: form.accountType === "Event" ? form.validTo : null,
		})
	);
	if (done) resetForm();
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
