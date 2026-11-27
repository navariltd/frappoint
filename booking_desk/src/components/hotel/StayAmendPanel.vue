<template>
	<section
		class="rounded-xl border border-primary bg-surface-container-lowest p-4 space-y-3"
		aria-label="Amend the stay"
	>
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-[15px] font-semibold">Amend the stay</h2>
			<button
				type="button"
				class="text-[12px] font-semibold text-on-surface-variant"
				@click="emit('close')"
			>
				Close
			</button>
		</div>
		<p class="text-[12px] text-on-surface-variant">
			New dates, room type, rate plan or guests, before arrival. The stay is priced again at
			today's rates; its rooms are swapped only if the new ones are free.
		</p>

		<div class="grid gap-3 grid-cols-2 sm:grid-cols-4">
			<label class="text-[12px] text-on-surface-variant">
				Arrives
				<input
					v-model="form.arrival"
					type="date"
					:min="businessDate"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
				/>
			</label>
			<label class="text-[12px] text-on-surface-variant">
				Leaves
				<input
					v-model="form.departure"
					type="date"
					:min="form.arrival"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
				/>
			</label>
			<label class="text-[12px] text-on-surface-variant">
				Adults
				<input
					v-model.number="form.adults"
					type="number"
					min="1"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
				/>
			</label>
			<label class="text-[12px] text-on-surface-variant">
				Children
				<input
					v-model.number="form.children"
					type="number"
					min="0"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
				/>
			</label>
		</div>
		<button
			type="button"
			class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
			:disabled="busy || !valid"
			@click="search"
		>
			Find rooms and rates
		</button>

		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-3 py-2 text-[12px]">
			{{ error }}
		</p>

		<ul v-if="options.length" class="space-y-1">
			<li
				v-for="option in options"
				:key="`${option.room_type}|${option.rate_plan}`"
				class="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-[13px]"
				:class="
					option.offered
						? 'border-outline-variant'
						: 'border-dashed border-outline-variant'
				"
			>
				<span class="min-w-0">
					<b>{{ option.room_type_name }}</b>
					<span class="text-on-surface-variant"> · {{ option.rate_plan_name }}</span>
					<span
						v-if="isCurrent(option)"
						class="ml-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold"
						>current</span
					>
					<span
						v-if="!option.offered"
						class="block text-[11px] text-on-surface-variant"
						>{{ option.reasons.join(", ") }}</span
					>
				</span>
				<span class="flex items-center gap-3">
					<span v-if="option.offered || option.overridable" class="tabular-nums">
						{{ formatMoney(option.total, option.currency) }}
					</span>
					<button
						type="button"
						class="rounded-lg bg-primary text-on-primary px-3 py-1 text-[12px] font-semibold disabled:opacity-40"
						:disabled="busy || !choosable(option)"
						@click="choose(option)"
					>
						Amend
					</button>
				</span>
			</li>
		</ul>
	</section>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { amendStayApi, hotelErrorMessage, searchAvailabilityApi } from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

// Change a stay that hasn't arrived. Options come from the same availability search as a new
// reservation; the server re-checks everything and swaps the rooms under its lock.
const props = defineProps({
	stay: { type: Object, required: true },
	businessDate: { type: String, default: "" },
	canOverrideRestrictions: { type: Boolean, default: false },
});
const emit = defineEmits(["done", "close"]);
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();

const form = reactive({
	arrival: props.stay.arrival_date,
	departure: props.stay.departure_date,
	adults: props.stay.adults,
	children: props.stay.children || 0,
});
const options = ref([]);
const busy = ref(false);
const error = ref("");

const valid = computed(
	() => form.arrival && form.departure && form.departure > form.arrival && form.adults >= 1
);
const isCurrent = (option) =>
	option.room_type === props.stay.room_type && option.rate_plan === props.stay.rate_plan;
// A sold-out current room type may only look full because the stay itself holds the room.
const choosable = (option) =>
	option.offered || isCurrent(option) || (option.overridable && props.canOverrideRestrictions);

async function search() {
	busy.value = true;
	error.value = "";
	try {
		options.value =
			(await searchAvailabilityApi({
				property: props.stay.property,
				arrival: form.arrival,
				departure: form.departure,
				adults: form.adults,
				children: form.children,
			})) || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		busy.value = false;
	}
}

async function choose(option) {
	const needsOverride = !option.offered && option.overridable && !isCurrent(option);
	const answer = await ask({
		title: `Amend to ${option.room_type_name}, ${option.rate_plan_name}?`,
		message: `${formatNight(form.arrival)} to ${formatNight(form.departure)}, ${
			form.adults
		} adult(s)${form.children ? `, ${form.children} child(ren)` : ""}. Now ${formatMoney(
			props.stay.total_amount,
			props.stay.currency
		)}${option.offered ? `, after ${formatMoney(option.total, option.currency)}` : ""}.`,
		reasonLabel: needsOverride ? `Why book against: ${option.reasons.join(", ")}` : undefined,
		confirmLabel: "Amend the stay",
		tone: needsOverride ? "warning" : "info",
	});
	if (!answer) return;
	busy.value = true;
	error.value = "";
	try {
		const result = await amendStayApi(props.stay.name, {
			arrival: form.arrival,
			departure: form.departure,
			roomType: option.room_type,
			ratePlan: option.rate_plan,
			adults: form.adults,
			children: form.children,
			overrideReason: needsOverride ? answer.reason : null,
		});
		emit("done", result?.amendment);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		busy.value = false;
	}
}
</script>
