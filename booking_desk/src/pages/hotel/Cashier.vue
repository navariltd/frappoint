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
				<header>
					<h1 class="text-[22px] font-semibold text-on-surface">Cashier</h1>
					<p class="text-[13px] text-on-surface-variant">
						{{ hotel.currentProperty?.property_name }} · Payments are taken in your own
						open shift.
					</p>
				</header>

				<!-- Open a shift -->
				<form
					v-if="!shift"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
					@submit.prevent="openShift"
				>
					<h2 class="text-[15px] font-semibold">Open a shift</h2>
					<div class="grid gap-3 sm:grid-cols-3">
						<label class="text-[12px] text-on-surface-variant">
							Opening float (cash in the drawer)
							<input
								v-model.number="openingFloat"
								type="number"
								min="0"
								step="0.01"
								class="cashier-input"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Workstation
							<input
								v-model="workstation"
								class="cashier-input"
								placeholder="e.g. Front desk 1"
							/>
						</label>
					</div>
					<button
						type="submit"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy"
					>
						Open shift
					</button>
				</form>

				<!-- The open shift -->
				<section
					v-else
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<div class="flex items-center gap-3">
								<h2 class="text-[15px] font-semibold">{{ shift.name }}</h2>
								<HotelStatusBadge :status="shift.status" />
							</div>
							<p class="text-[12px] text-on-surface-variant">
								Opened {{ formatTimestamp(shift.opened_at) }}
								<template v-if="shift.workstation">
									· {{ shift.workstation }}</template
								>
								· Float {{ money(shift.opening_float) }}
								<template v-if="shift.float_mode_of_payment">
									in {{ shift.float_mode_of_payment }}</template
								>
							</p>
						</div>
					</div>

					<div>
						<p class="text-[12px] font-semibold">Payments in this shift</p>
						<p
							v-if="!shift.payments.length"
							class="text-[12px] text-on-surface-variant"
						>
							None yet. Take payments from a stay's folios.
						</p>
						<table v-else class="mt-1 w-full text-[12px]">
							<tbody>
								<tr
									v-for="payment in shift.payments"
									:key="payment.name"
									class="border-b border-outline-variant"
								>
									<td class="py-1.5">{{ formatTimestamp(payment.creation) }}</td>
									<td class="py-1.5">
										{{ payment.payer_name }}
										<span class="text-on-surface-variant">
											· {{ payment.mode_of_payment }}
											<template v-if="payment.reference_no">
												· {{ payment.reference_no }}</template
											>
										</span>
									</td>
									<td class="py-1.5">
										<HotelStatusBadge :status="paymentLabel(payment)" />
									</td>
									<td class="py-1.5 text-right whitespace-nowrap">
										{{ payment.payment_type === "Refund" ? "−" : ""
										}}{{ money(payment.amount) }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Blind close -->
					<form
						class="space-y-2 border-t border-outline-variant pt-3"
						@submit.prevent="closeShift"
					>
						<p class="text-[13px] font-semibold">Close shift</p>
						<p class="text-[12px] text-on-surface-variant">
							Count each tender and enter what you have. The expected totals are
							shown only after you close. Explain any difference.
						</p>
						<div
							v-for="mode in closeModes"
							:key="mode"
							class="grid gap-2 sm:grid-cols-[1fr_1fr_2fr] items-end"
						>
							<span class="text-[13px]">{{ mode }}</span>
							<label class="text-[12px] text-on-surface-variant">
								Counted
								<input
									v-model.number="declared[mode]"
									type="number"
									min="0"
									step="0.01"
									class="cashier-input"
								/>
							</label>
							<label class="text-[12px] text-on-surface-variant">
								Reason for any difference
								<input v-model="reasons[mode]" class="cashier-input" />
							</label>
						</div>
						<button
							type="submit"
							class="rounded-lg border border-outline-variant px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="busy"
						>
							Close shift
						</button>
					</form>
				</section>

				<!-- Result of the close -->
				<section
					v-if="closed"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				>
					<h2 class="text-[15px] font-semibold">{{ closed.name }} closed</h2>
					<CountsTable :counts="closed.counts" :money="money" />
					<p class="mt-2 text-[12px] text-on-surface-variant">
						A supervisor reviews the shift. Any difference is then posted to cash
						over/short.
					</p>
				</section>

				<!-- Supervisor review -->
				<section
					v-if="data.can_review && data.to_review.length"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
				>
					<h2 class="text-[15px] font-semibold">Shifts to review</h2>
					<div
						v-for="item in data.to_review"
						:key="item.name"
						class="rounded-lg border border-outline-variant p-3 space-y-2"
					>
						<p class="text-[13px] font-semibold">
							{{ item.name }} · {{ item.cashier }}
							<span class="font-normal text-on-surface-variant">
								· closed {{ formatTimestamp(item.closed_at) }}</span
							>
						</p>
						<CountsTable :counts="item.counts" :money="money" />
						<div class="flex flex-wrap items-end gap-2">
							<label class="flex-1 text-[12px] text-on-surface-variant">
								Review notes
								<input v-model="notes[item.name]" class="cashier-input" />
							</label>
							<button
								type="button"
								class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
								:disabled="busy"
								@click="review(item)"
							>
								Accept shift
							</button>
						</div>
					</div>
				</section>

				<section
					v-if="data.recent.length"
					class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
				>
					<h2 class="text-[15px] font-semibold">Your recent shifts</h2>
					<table class="mt-2 w-full text-[12px]">
						<tbody>
							<tr
								v-for="past in data.recent"
								:key="past.name"
								class="border-b border-outline-variant"
							>
								<td class="py-1.5">{{ past.name }}</td>
								<td class="py-1.5">{{ formatNight(past.business_date) }}</td>
								<td class="py-1.5">{{ past.status }}</td>
								<td class="py-1.5 text-right text-on-surface-variant">
									{{ formatTimestamp(past.closed_at) }}
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
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from "vue";
import {
	closeShiftApi,
	fetchCashierApi,
	hotelErrorMessage,
	openShiftApi,
	reviewShiftApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import HotelUnavailable from "@/components/hotel/HotelUnavailable.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { useHotelStore } from "@/stores/hotel.store";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

/** Expected, declared and variance per tender, as a small table. */
const CountsTable = defineComponent({
	props: {
		counts: { type: Array, default: () => [] },
		money: { type: Function, required: true },
	},
	setup(props) {
		const cell = (text, extra = "") => h("td", { class: `py-1.5 ${extra}` }, text);
		return () =>
			h("table", { class: "mt-2 w-full text-[12px]" }, [
				h("thead", { class: "text-left text-on-surface-variant" }, [
					h("tr", [
						cell("Tender"),
						cell("Expected", "text-right"),
						cell("Counted", "text-right"),
						cell("Difference", "text-right"),
						cell("Reason", "pl-3"),
					]),
				]),
				h(
					"tbody",
					props.counts.map((row) =>
						h(
							"tr",
							{ key: row.mode_of_payment, class: "border-t border-outline-variant" },
							[
								cell(row.mode_of_payment),
								cell(props.money(row.expected), "text-right"),
								cell(props.money(row.declared), "text-right"),
								cell(
									props.money(row.variance),
									`text-right font-semibold ${
										Number(row.variance) ? "text-error" : ""
									}`
								),
								cell(row.variance_reason || "", "pl-3 text-on-surface-variant"),
							]
						)
					)
				),
			]);
	},
});

const hotel = useHotelStore();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const closed = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const openingFloat = ref(0);
const workstation = ref("");
const declared = reactive({});
const reasons = reactive({});
const notes = reactive({});

const shift = computed(() => data.value?.shift || null);
const closeModes = computed(() => {
	const modes = new Set([...(shift.value?.modes || []), ...(data.value?.options?.modes || [])]);
	return [...modes].sort();
});
const blocked = computed(() => {
	if (hotel.error) return hotel.error;
	if (!hotel.loaded) return "";
	if (!hotel.enabled) return "Hospitality is not enabled on this site.";
	if (!hotel.properties.length) return "You don't have access to any active hotel property.";
	return "";
});

function money(amount) {
	return formatMoney(amount, hotel.currentProperty?.currency);
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

function paymentLabel(payment) {
	return payment.payment_type === "Refund" ? "Refund" : payment.status;
}

async function load() {
	if (!hotel.property) return;
	loading.value = true;
	error.value = "";
	try {
		data.value = await fetchCashierApi(hotel.property);
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

function openShift() {
	run(() => openShiftApi(hotel.property, openingFloat.value, workstation.value));
}

async function closeShift() {
	const answer = await ask({
		title: `Close ${shift.value.name}?`,
		message: "You can't take payments in this shift after closing it.",
		confirmLabel: "Close shift",
	});
	if (!answer) return;
	const counts = Object.fromEntries(closeModes.value.map((mode) => [mode, declared[mode] || 0]));
	const ok = await run(() => closeShiftApi(shift.value.name, counts, { ...reasons }));
	if (ok) {
		closed.value = data.value.closed;
		const off = closed.value.counts.filter((row) => Number(row.variance));
		notify({
			tone: off.length ? "warning" : "info",
			title: off.length
				? "Shift closed with a difference"
				: "Shift closed. Your count matches.",
			message: off.length
				? off.map((row) => `${row.mode_of_payment}: ${money(row.variance)}`).join(", ")
				: "",
		});
	}
}

async function review(item) {
	const off = item.counts.filter((row) => Number(row.variance));
	const answer = await ask({
		title: `Accept ${item.name}?`,
		message: off.length
			? `The differences (${off
					.map((row) => `${row.mode_of_payment} ${money(row.variance)}`)
					.join(", ")}) post to cash over/short.`
			: "The counts match. Nothing is posted.",
		confirmLabel: "Accept shift",
	});
	if (answer) run(() => reviewShiftApi(item.name, notes[item.name]));
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
.cashier-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
