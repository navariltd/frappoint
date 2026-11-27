<template>
	<aside
		class="fixed inset-x-0 bottom-0 z-40 max-h-[75vh] overflow-y-auto rounded-t-2xl border border-outline-variant bg-surface-container-lowest p-4 shadow-xl sm:inset-x-auto sm:bottom-auto sm:right-4 sm:top-20 sm:max-h-[calc(100vh-6rem)] sm:w-[380px] sm:rounded-2xl"
		role="dialog"
		aria-modal="false"
		:aria-label="`Rooms for ${target.guest || target.stay}`"
		@keydown.esc="emit('close')"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 class="truncate text-[15px] font-semibold">
					{{ target.guest || target.stay }}
				</h2>
				<p class="text-[12px] text-on-surface-variant">
					{{ shortDate(target.arrival) }} – {{ shortDate(target.to) }} ·
					{{
						target.roomNumber
							? `${target.action === "move" ? "In" : "Has"} room ${
									target.roomNumber
							  }`
							: "No room yet"
					}}
				</p>
			</div>
			<button
				ref="closeButton"
				type="button"
				class="material-symbols-outlined rounded-lg p-1 text-[20px] text-on-surface-variant hover:bg-surface-container"
				aria-label="Close"
				@click="emit('close')"
			>
				close
			</button>
		</div>

		<!-- The page's questions (confirm, give a reason) while the panel covers the page -->
		<ActionBanner
			class="mt-3"
			:banner="banner"
			:busy="busy"
			@confirm="(reason) => emit('confirm', reason)"
			@cancel="emit('cancel')"
		/>

		<div class="mt-2 flex flex-wrap gap-2 text-[12px] font-semibold">
			<button type="button" class="text-primary" @click="emit('open')">Open stay →</button>
			<button
				v-if="canChange && target.room && target.action === 'assign'"
				type="button"
				class="text-error disabled:opacity-50"
				:disabled="busy"
				@click="emit('unassign')"
			>
				Unassign room {{ target.roomNumber }}
			</button>
		</div>

		<p
			v-if="!canChange"
			class="mt-3 rounded-lg bg-surface-container px-3 py-2 text-[12px] text-on-surface-variant"
		>
			{{ target.why || "This stay can't change rooms here." }}
		</p>

		<template v-else>
			<p class="mt-3 text-[12px] font-semibold">
				{{ target.action === "move" ? "Move the guest now to" : "Give the stay" }}
			</p>
			<p v-if="ranking?.personalised" class="text-[11px] text-on-surface-variant">
				Ranked for
				{{
					ranking.rules.map((rule) => rule.label).join(", ") || "the guest's past stays"
				}}.
			</p>
			<p v-if="error" class="mt-2 rounded-lg bg-error-container/40 px-3 py-2 text-[12px]">
				{{ error }}
			</p>
			<p v-else-if="loading" class="mt-2 text-[12px] text-on-surface-variant">
				Loading rooms…
			</p>
			<p
				v-else-if="ranking?.no_room_meets_required"
				class="mt-2 rounded-lg bg-error-container/40 px-3 py-2 text-[12px]"
			>
				No room meets every required preference. Pick one below and give a reason, or
				change the dates or room type.
			</p>

			<ol class="mt-2 space-y-1">
				<li v-for="room in rooms" :key="room.name">
					<div
						class="flex items-start gap-3 rounded-lg border px-3 py-2"
						:class="
							room.is_current
								? 'border-primary bg-primary/10'
								: room.eligible
								? 'border-outline-variant'
								: 'border-dashed border-outline-variant'
						"
					>
						<span
							class="w-5 shrink-0 pt-0.5 text-[12px] font-semibold text-on-surface-variant"
							>{{ room.rank || "–" }}</span
						>
						<span class="min-w-0 flex-1 text-[12px]">
							<span class="text-[13px] font-semibold">{{ room.room_number }}</span>
							<span class="text-on-surface-variant">
								· {{ room.housekeeping_condition
								}}<template v-if="room.floor != null">
									· floor {{ room.floor }}</template
								><template v-if="room.is_current"> · current</template></span
							>
							<span v-if="room.matched?.length || room.missed?.length" class="block">
								<span
									v-for="text in room.matched"
									:key="`m-${text}`"
									class="mr-2 text-primary"
									>✓ {{ text }}</span
								><span
									v-for="text in room.missed"
									:key="`x-${text}`"
									class="mr-2 text-on-surface-variant"
									>✗ {{ text }}</span
								>
							</span>
							<span v-if="problem(room)" class="block text-error">{{
								problem(room)
							}}</span>
						</span>
						<button
							type="button"
							class="shrink-0 rounded-lg px-2.5 py-1 text-[12px] font-semibold disabled:opacity-40"
							:class="
								room.eligible
									? 'bg-primary text-on-primary'
									: 'border border-outline-variant text-on-surface'
							"
							:disabled="busy || !choosable(room)"
							@click="
								emit('choose', { name: room.name, room_number: room.room_number })
							"
						>
							{{ target.action === "move" ? "Move" : "Assign" }}
						</button>
					</div>
				</li>
			</ol>
		</template>
	</aside>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { fetchRankedRoomsApi, hotelErrorMessage } from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";

// The tap-and-keyboard way to do what dragging does on the tape chart: the stay's rooms, ranked
// for its guests, with Assign or Move on each, and Unassign. Choosing goes back to the page,
// which runs the same check, confirmation and command as a drop.
const props = defineProps({
	target: { type: Object, required: true },
	canMove: { type: Boolean, default: false },
	busy: { type: Boolean, default: false },
	banner: { type: Object, default: null },
});
const emit = defineEmits(["choose", "unassign", "open", "close", "confirm", "cancel"]);

const ranking = ref(null);
const loading = ref(false);
const error = ref("");
const closeButton = ref(null);

const canChange = computed(() => props.canMove && props.target.canChange);
const rooms = computed(() => ranking.value?.rooms || []);

function shortDate(value) {
	if (!value) return "";
	return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
		day: "numeric",
		month: "short",
	});
}

// Rooms a hard rule rules out can't be chosen. One that only misses a Required preference can,
// with a reason asked on the way.
function problem(room) {
	if (room.is_current) return "";
	const hard = room.blocked?.length
		? room.blocked
		: room.available
		? []
		: [room.unavailable_reason];
	if (hard.filter(Boolean).length) return hard.filter(Boolean).join(" · ");
	if (props.target.action === "move" && !room.ready)
		return `Not ready (${room.housekeeping_condition})`;
	return (room.excluded || []).join(" · ");
}

function choosable(room) {
	if (room.is_current) return false;
	if (room.blocked?.length || !room.available) return false;
	return !(props.target.action === "move" && !room.ready);
}

async function load() {
	ranking.value = null;
	error.value = "";
	if (!canChange.value) return;
	loading.value = true;
	try {
		ranking.value = await fetchRankedRoomsApi(props.target.stay);
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

watch(
	() => props.target.stay,
	async () => {
		await load();
		await nextTick();
		closeButton.value?.focus();
	},
	{ immediate: true }
);

defineExpose({ reload: load });
</script>
