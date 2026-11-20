<template>
	<section
		class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-4"
	>
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-[15px] font-semibold">Messages and traces</h2>
			<span v-if="editable" class="flex gap-3 text-[12px] font-semibold">
				<button type="button" class="text-primary" @click="openForm('message')">
					+ Message
				</button>
				<button type="button" class="text-primary" @click="openForm('trace')">
					+ Trace
				</button>
			</span>
		</div>

		<p v-if="error" class="rounded-lg bg-error-container/40 px-3 py-2 text-[12px]">
			{{ error }}
		</p>
		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>

		<!-- Take a message or set a trace -->
		<form
			v-if="form.kind"
			class="space-y-2 rounded-lg bg-surface-container-low p-3"
			@submit.prevent="save"
		>
			<template v-if="form.kind === 'message'">
				<div class="grid grid-cols-2 gap-2">
					<label class="text-[12px] text-on-surface-variant">
						For
						<select
							v-model="form.stayGuest"
							class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
						>
							<option value="">Whoever is in the room</option>
							<option v-for="guest in guests" :key="guest.name" :value="guest.name">
								{{ guest.guest_name }}
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						From
						<input
							v-model="form.sender"
							type="text"
							placeholder="Caller or visitor"
							class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
						/>
					</label>
				</div>
			</template>
			<div v-else class="grid grid-cols-3 gap-2">
				<label class="text-[12px] text-on-surface-variant">
					Department
					<select
						v-model="form.department"
						class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
					>
						<option v-for="department in DEPARTMENTS" :key="department">
							{{ department }}
						</option>
					</select>
				</label>
				<label class="text-[12px] text-on-surface-variant">
					Due
					<input
						v-model="form.dueDate"
						type="date"
						class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
					/>
				</label>
				<label class="text-[12px] text-on-surface-variant">
					At
					<input
						v-model="form.dueTime"
						type="time"
						class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
					/>
				</label>
			</div>
			<label class="block text-[12px] text-on-surface-variant">
				{{ form.kind === "message" ? "Message" : "What to do" }}
				<textarea
					v-model="form.text"
					rows="2"
					class="mt-1 block w-full rounded-lg border border-outline-variant px-2 py-1.5 text-[13px]"
				></textarea>
			</label>
			<div class="flex justify-end gap-2">
				<button
					type="button"
					class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold"
					@click="form.kind = null"
				>
					Cancel
				</button>
				<button
					type="submit"
					class="rounded-lg bg-primary px-3 py-1.5 text-[12px] font-semibold text-on-primary disabled:opacity-50"
					:disabled="
						busy || !form.text.trim() || (form.kind === 'trace' && !form.dueDate)
					"
				>
					Save
				</button>
			</div>
		</form>

		<!-- Messages: pending first -->
		<div class="space-y-1.5">
			<p class="text-[12px] font-semibold">Messages</p>
			<p v-if="!data.messages.length" class="text-[12px] text-on-surface-variant">
				No messages.
			</p>
			<ul v-else class="space-y-2">
				<li
					v-for="message in data.messages"
					:key="message.name"
					class="rounded-lg border px-3 py-2 text-[13px]"
					:class="
						message.status === 'Pending'
							? 'border-tertiary bg-tertiary-container/20'
							: 'border-outline-variant'
					"
				>
					<p>
						<b>{{ message.guest_name }}</b>
						<span v-if="message.sender" class="text-on-surface-variant">
							· from {{ message.sender }}</span
						>
						<span class="text-[11px] text-on-surface-variant">
							· {{ formatTimestamp(message.taken_at) }} · {{ message.status }}
							<template v-if="message.channel"> ({{ message.channel }})</template>
						</span>
					</p>
					<p class="text-[12px]">{{ message.message }}</p>
					<p v-if="message.notes" class="text-[11px] text-on-surface-variant">
						{{ message.notes }}
					</p>
					<span
						v-if="message.status === 'Pending' && editable"
						class="mt-1 flex flex-wrap items-center gap-2 text-[12px]"
					>
						<select
							v-model="channels[message.name]"
							class="rounded border border-outline-variant px-2 py-0.5 text-[12px]"
						>
							<option v-for="channel in CHANNELS" :key="channel">
								{{ channel }}
							</option>
						</select>
						<button
							type="button"
							class="font-semibold text-primary"
							:disabled="busy"
							@click="deliver(message)"
						>
							Delivered
						</button>
						<button
							type="button"
							class="text-on-surface-variant"
							:disabled="busy"
							@click="fail(message)"
						>
							Couldn't deliver
						</button>
					</span>
				</li>
			</ul>
		</div>

		<!-- Traces: open first -->
		<div class="space-y-1.5">
			<p class="text-[12px] font-semibold">Traces</p>
			<p v-if="!data.traces.length" class="text-[12px] text-on-surface-variant">
				No follow-ups.
			</p>
			<ul v-else class="space-y-1.5">
				<li
					v-for="trace in data.traces"
					:key="trace.name"
					class="flex flex-wrap items-start justify-between gap-2 text-[13px]"
				>
					<span class="min-w-0">
						<b>{{ trace.department }}</b>
						<span class="text-[11px] text-on-surface-variant">
							· {{ formatNight(trace.due_date) }}
							<template v-if="trace.due_time">
								{{ String(trace.due_time).slice(0, 5) }}</template
							>
							· {{ trace.status }}</span
						>
						<span class="block text-[12px]">{{ trace.text }}</span>
						<span v-if="trace.notes" class="block text-[11px] text-on-surface-variant">
							{{ trace.notes }}
						</span>
					</span>
					<span
						v-if="trace.status === 'Open' && editable"
						class="flex gap-2 text-[12px]"
					>
						<button
							type="button"
							class="font-semibold text-primary"
							:disabled="busy"
							@click="resolve(trace)"
						>
							Done
						</button>
						<button
							type="button"
							class="text-on-surface-variant"
							:disabled="busy"
							@click="cancelTrace(trace)"
						>
							Cancel
						</button>
					</span>
				</li>
			</ul>
		</div>

		<!-- What the guests were sent -->
		<div v-if="data.notifications?.length" class="space-y-1">
			<p class="text-[12px] font-semibold">Sent to the guests</p>
			<ul class="space-y-0.5 text-[12px] text-on-surface-variant">
				<li v-for="row in data.notifications" :key="row.name">
					{{ row.event }} · {{ row.channel }} · {{ row.status }}
					<template v-if="row.recipient"> · {{ row.recipient }}</template>
					<template v-if="row.error"> · {{ row.error }}</template>
				</li>
			</ul>
		</div>
	</section>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import {
	addTraceApi,
	closeMessageApi,
	closeTraceApi,
	fetchGuestMessagesApi,
	hotelErrorMessage,
	takeMessageApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatNight } from "@/utils/hotelFormat";

const DEPARTMENTS = [
	"Front Desk",
	"Housekeeping",
	"Concierge",
	"Food and Beverage",
	"Maintenance",
];
const CHANNELS = ["In Person", "SMS", "Email", "Portal"];

// A stay's messages for its guests, departments' follow-ups (traces), and what the guests were sent.
const props = defineProps({
	stayId: { type: String, required: true },
	guests: { type: Array, default: () => [] },
	businessDate: { type: String, default: "" },
	editable: { type: Boolean, default: true },
});
const emit = defineEmits(["changed"]);
const { banner, ask, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();

const data = ref({ messages: [], traces: [], notifications: [] });
const busy = ref(false);
const error = ref("");
const channels = reactive({});
const blank = () => ({
	kind: null,
	stayGuest: "",
	sender: "",
	department: "Front Desk",
	dueDate: props.businessDate,
	dueTime: "",
	text: "",
});
const form = reactive(blank());

function formatTimestamp(value) {
	if (!value) return "";
	return new Date(String(value).replace(" ", "T")).toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function openForm(kind) {
	Object.assign(form, blank(), { kind });
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		data.value = await command();
		emit("changed");
		return true;
	} catch (e) {
		error.value = hotelErrorMessage(e);
		return false;
	} finally {
		busy.value = false;
	}
}

async function load() {
	try {
		data.value = await fetchGuestMessagesApi(props.stayId);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	}
}

async function save() {
	const text = form.text.trim();
	const saved = await run(() =>
		form.kind === "message"
			? takeMessageApi(props.stayId, text, form.sender || null, form.stayGuest || null)
			: addTraceApi(props.stayId, { ...form, text })
	);
	if (saved) form.kind = null;
}

function deliver(message) {
	run(() => closeMessageApi(message.name, true, channels[message.name] || "In Person"));
}

async function fail(message) {
	const answer = await ask({
		title: `Couldn't deliver the message for ${message.guest_name}?`,
		reasonLabel: "What happened",
		confirmLabel: "Mark failed",
	});
	if (answer) run(() => closeMessageApi(message.name, false, null, answer.reason));
}

function resolve(trace) {
	run(() => closeTraceApi(trace.name, true));
}

async function cancelTrace(trace) {
	const answer = await ask({
		title: "Cancel this follow-up?",
		reasonLabel: "Why it's no longer needed",
		confirmLabel: "Cancel trace",
	});
	if (answer) run(() => closeTraceApi(trace.name, false, answer.reason));
}

watch(() => props.stayId, load, { immediate: true });
</script>
