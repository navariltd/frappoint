<template>
	<section
		v-if="share && (share.shared || share.can_join)"
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
		aria-label="Room share"
	>
		<div class="flex flex-wrap items-center justify-between gap-2">
			<h2 class="text-[15px] font-semibold">Room share</h2>
			<button
				v-if="!share.shared && !picking"
				type="button"
				class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
				:disabled="busy"
				@click="startPicking"
			>
				Share a room with another stay
			</button>
		</div>
		<p class="text-[12px] text-on-surface-variant">
			<template v-if="share.shared">
				These stays share one room. Each keeps its own dates, folio and check-out; the room
				is counted once and its charge on the nights they share is split as below.
			</template>
			<template v-else>
				Put this stay in the room of another stay of the same room type. Each keeps its own
				bill.
			</template>
		</p>

		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-3 py-2 text-[12px]">
			{{ error }}
		</p>

		<!-- Who shares the room -->
		<ul v-if="share.shared" class="space-y-1">
			<li
				v-for="member in share.members"
				:key="member.stay"
				class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
			>
				<span class="min-w-0">
					<b>{{ member.guest }}</b>
					<span
						v-if="member.stay === stay.name"
						class="ml-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold"
						>this stay</span
					>
					<span
						v-if="member.stay === share.primary"
						class="ml-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold"
						>primary</span
					>
					<span class="block text-[11px] text-on-surface-variant">
						{{ formatNight(member.start_date) }} to
						{{ formatNight(member.end_date) }} · {{ member.status }} ·
						{{ member.adults }} adult(s)<template v-if="member.children"
							>, {{ member.children }} child(ren)</template
						>
					</span>
				</span>
				<span class="text-right">
					<span class="block tabular-nums">{{
						formatMoney(member.room_charge, member.currency)
					}}</span>
					<span class="block text-[11px] text-on-surface-variant">room, all nights</span>
				</span>
			</li>
		</ul>

		<!-- Pick a stay to share with -->
		<div v-if="picking" class="space-y-2">
			<p v-if="!candidates.length" class="text-[12px] text-on-surface-variant">
				No other {{ stay.room_type_name || "stay of this room type" }} overlaps these
				dates.
			</p>
			<ul v-else class="space-y-1">
				<li
					v-for="candidate in candidates"
					:key="candidate.name"
					class="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-[13px]"
					:class="
						target === candidate.name ? 'border-primary' : 'border-outline-variant'
					"
				>
					<span class="min-w-0">
						<b>{{ candidate.lead_guest_name }}</b>
						<span class="text-on-surface-variant"> · {{ candidate.name }}</span>
						<span
							v-if="!candidate.same_booking"
							class="ml-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold"
							>another booking</span
						>
						<span
							v-if="candidate.shared"
							class="ml-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold"
							>already shared</span
						>
						<span class="block text-[11px] text-on-surface-variant">
							{{ formatNight(candidate.arrival_date) }} to
							{{ formatNight(candidate.departure_date) }} · {{ candidate.status }} ·
							{{ candidate.adults }} adult(s)
						</span>
					</span>
					<button
						type="button"
						class="rounded-lg border border-outline-variant px-3 py-1 text-[12px] font-semibold disabled:opacity-40"
						:disabled="
							busy || (!candidate.same_booking && !share.can_combine_bookings)
						"
						:title="
							!candidate.same_booking && !share.can_combine_bookings
								? 'A manager combines stays from different bookings'
								: ''
						"
						@click="target = candidate.name"
					>
						{{ target === candidate.name ? "Selected" : "Select" }}
					</button>
				</li>
			</ul>
			<div class="flex justify-end">
				<button
					type="button"
					class="text-[12px] font-semibold text-on-surface-variant"
					@click="stopPicking"
				>
					Close
				</button>
			</div>
		</div>

		<!-- How the room charge is split -->
		<div
			v-if="(share.shared && share.can_change_method) || (picking && target)"
			class="grid gap-3 grid-cols-1 sm:grid-cols-3 border-t border-outline-variant pt-3"
		>
			<label class="text-[12px] text-on-surface-variant">
				Room charge
				<select
					v-model="form.method"
					class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
				>
					<option v-for="method in share.methods" :key="method" :value="method">
						{{ METHOD_LABELS[method] || method }}
					</option>
				</select>
			</label>
			<label v-if="form.method === 'Percentage'" class="text-[12px] text-on-surface-variant">
				{{ primaryName }} pays (%)
				<input
					v-model.number="form.percent"
					type="number"
					min="0"
					max="100"
					step="0.01"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
				/>
			</label>
			<label
				v-if="form.method === 'Entire to One'"
				class="text-[12px] text-on-surface-variant"
			>
				Who pays the room
				<select
					v-model="form.payer"
					class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
				>
					<option v-for="option in payerOptions" :key="option.stay" :value="option.stay">
						{{ option.guest }}
					</option>
				</select>
			</label>
			<div class="flex items-end sm:col-start-3">
				<button
					type="button"
					class="w-full rounded-lg bg-primary text-on-primary px-3 py-2 text-[12px] font-semibold disabled:opacity-50"
					:disabled="busy || !formValid"
					@click="share.shared ? changeMethod() : join()"
				>
					{{ share.shared ? "Change the split" : "Share the room" }}
				</button>
			</div>
			<p class="text-[11px] text-on-surface-variant sm:col-span-3">
				{{ METHOD_HELP[form.method] }} Nights already charged don't change.
			</p>
		</div>

		<div v-if="share.can_separate" class="flex justify-end">
			<button
				type="button"
				class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
				:disabled="busy"
				@click="separate"
			>
				Give this stay its own room
			</button>
		</div>
	</section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
	fetchRoomShareApi,
	fetchShareCandidatesApi,
	hotelErrorMessage,
	separateRoomShareApi,
	setRoomShareMethodApi,
	shareRoomApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

// Independent sharers (R2-1): stays that share one room while each keeps its own bill. The server
// checks everything again (setting, roles, capacity, dates) and takes the rooms under its lock.
const props = defineProps({
	stay: { type: Object, required: true },
});
const emit = defineEmits(["changed"]);
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();

const METHOD_LABELS = {
	"Own Rate": "Each pays their own rate",
	"Equal Split": "Split equally",
	Percentage: "Split by percentage",
	"Entire to One": "One guest pays the room",
};
const METHOD_HELP = {
	"Own Rate": "Each stay pays the room rate it was booked at.",
	"Equal Split":
		"The room rate of the primary stay is split equally on the nights they share; a cent left over goes to the primary stay.",
	Percentage:
		"The primary stay pays its percentage of the room rate on the nights they share; the others share the rest.",
	"Entire to One":
		"One stay pays the whole room on the nights they share; the others pay only their own extras.",
};

const share = ref(null);
const candidates = ref([]);
const picking = ref(false);
const target = ref("");
const busy = ref(false);
const error = ref("");
const form = reactive({ method: "Equal Split", percent: 50, payer: "" });

const targetStay = computed(() => candidates.value.find((row) => row.name === target.value));
const payerOptions = computed(() => {
	if (share.value?.shared) {
		return share.value.members
			.filter((member) => !["Checked Out"].includes(member.status))
			.map((member) => ({ stay: member.stay, guest: member.guest }));
	}
	const options = [{ stay: props.stay.name, guest: props.stay.lead_guest_name }];
	if (targetStay.value) {
		options.push({ stay: targetStay.value.name, guest: targetStay.value.lead_guest_name });
	}
	return options;
});
const primaryName = computed(() => {
	if (share.value?.shared) {
		return (
			share.value.members.find((member) => member.stay === share.value.primary)?.guest ||
			"The primary stay"
		);
	}
	// Joining: the other stay's room is shared, so it is the primary stay.
	return targetStay.value?.lead_guest_name || "The primary stay";
});
const formValid = computed(() => {
	if (!share.value?.shared && !target.value) return false;
	if (form.method === "Percentage") return form.percent >= 0 && form.percent <= 100;
	if (form.method === "Entire to One") return !!form.payer;
	return true;
});

async function load() {
	error.value = "";
	try {
		share.value = await fetchRoomShareApi(props.stay.name);
		if (share.value?.shared) {
			form.method = share.value.method || "Equal Split";
			form.percent = share.value.percent || 50;
			form.payer = share.value.payer || "";
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	}
}

async function startPicking() {
	picking.value = true;
	target.value = "";
	busy.value = true;
	try {
		candidates.value = (await fetchShareCandidatesApi(props.stay.name)) || [];
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		busy.value = false;
	}
}

function stopPicking() {
	picking.value = false;
	target.value = "";
}

async function run(command, title) {
	busy.value = true;
	error.value = "";
	try {
		share.value = await command();
		picking.value = false;
		target.value = "";
		emit("changed");
		notify({ title });
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		busy.value = false;
	}
}

const methodText = () =>
	form.method === "Percentage"
		? `${primaryName.value} pays ${form.percent}%`
		: form.method === "Entire to One"
		? `${payerOptions.value.find((row) => row.stay === form.payer)?.guest} pays the room`
		: METHOD_LABELS[form.method];

async function join() {
	const other = targetStay.value;
	const answer = await ask({
		title: `Share ${other.lead_guest_name}'s room?`,
		message: `${props.stay.lead_guest_name} gives up their own room and moves into ${
			other.lead_guest_name
		}'s from ${formatNight(props.stay.arrival_date)}. ${methodText()}.${
			other.same_booking ? "" : " The two bookings stay separate."
		}`,
		confirmLabel: "Share the room",
		tone: "info",
	});
	if (!answer) return;
	await run(
		() =>
			shareRoomApi(props.stay.name, {
				withStay: other.name,
				method: form.method,
				percent: form.method === "Percentage" ? form.percent : null,
				payer: form.method === "Entire to One" ? form.payer : null,
			}),
		"The room is shared"
	);
}

async function changeMethod() {
	await run(
		() =>
			setRoomShareMethodApi(props.stay.name, {
				method: form.method,
				percent: form.method === "Percentage" ? form.percent : null,
				payer: form.method === "Entire to One" ? form.payer : null,
			}),
		"The room charge split changed"
	);
}

async function separate() {
	const answer = await ask({
		title: "Give this stay its own room?",
		message: `${props.stay.lead_guest_name} takes a room of their own again, at their own rate, if one is free.`,
		reasonLabel: "Why is the stay leaving the share?",
		confirmLabel: "Separate",
		tone: "warning",
	});
	if (!answer) return;
	await run(
		() => separateRoomShareApi(props.stay.name, answer.reason),
		"The stay has its own room"
	);
}

watch(
	() => form.method,
	(method) => {
		if (method === "Entire to One" && !form.payer)
			form.payer = payerOptions.value[0]?.stay || "";
	}
);
watch(() => props.stay.name, load);
onMounted(load);
</script>
