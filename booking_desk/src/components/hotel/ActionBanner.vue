<template>
	<div
		v-if="banner"
		ref="root"
		:role="banner.kind === 'ask' ? 'alertdialog' : 'status'"
		:aria-labelledby="titleId"
		aria-live="polite"
		class="sticky top-3 z-30 rounded-xl border px-4 py-3 shadow-sm"
		:class="tone.box"
		@keydown.esc.prevent="$emit('cancel')"
	>
		<div class="flex items-start gap-3">
			<span
				class="material-symbols-outlined text-[20px]"
				:class="tone.icon"
				aria-hidden="true"
				>{{ tone.symbol }}</span
			>
			<div class="min-w-0 flex-1 space-y-1">
				<p :id="titleId" class="text-[13px] font-semibold text-on-surface">
					{{ banner.title }}
				</p>
				<p v-if="banner.message" class="text-[12px] text-on-surface-variant">
					{{ banner.message }}
				</p>

				<form
					v-if="banner.kind === 'ask'"
					class="flex flex-wrap items-end gap-2 pt-1"
					@submit.prevent="submit"
				>
					<label
						v-if="banner.reasonLabel"
						class="min-w-[220px] flex-1 text-[12px] text-on-surface-variant"
					>
						{{ banner.reasonLabel }}
						<input
							ref="reasonInput"
							v-model="reason"
							required
							class="mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
							:placeholder="banner.reasonPlaceholder || ''"
						/>
					</label>
					<button
						type="button"
						class="rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[12px] font-semibold text-on-surface"
						@click="$emit('cancel')"
					>
						{{ banner.cancelLabel }}
					</button>
					<button
						ref="confirmButton"
						type="submit"
						class="rounded-lg px-3 py-2 text-[12px] font-semibold disabled:opacity-50"
						:class="tone.button"
						:disabled="busy || (!!banner.reasonLabel && !reason.trim())"
					>
						{{ banner.confirmLabel }}
					</button>
				</form>
			</div>
			<button
				v-if="banner.kind === 'notice'"
				type="button"
				class="material-symbols-outlined text-[18px] text-on-surface-variant"
				aria-label="Dismiss"
				@click="$emit('cancel')"
			>
				close
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
	banner: { type: Object, default: null },
	busy: { type: Boolean, default: false },
});
const emit = defineEmits(["confirm", "cancel"]);

const TONES = {
	info: {
		box: "border-primary bg-surface-container-lowest",
		icon: "text-primary",
		symbol: "info",
		button: "bg-primary text-on-primary",
	},
	warning: {
		box: "border-tertiary bg-surface-container-lowest",
		icon: "text-tertiary",
		symbol: "help",
		button: "bg-primary text-on-primary",
	},
	danger: {
		box: "border-error bg-surface-container-lowest",
		icon: "text-error",
		symbol: "warning",
		button: "bg-error text-on-error",
	},
};

const titleId = `action-banner-${Math.random().toString(36).slice(2, 8)}`;
const root = ref(null);
const reasonInput = ref(null);
const confirmButton = ref(null);
const reason = ref("");

const tone = computed(() => TONES[props.banner?.tone] || TONES.info);

function submit() {
	if (props.banner?.reasonLabel && !reason.value.trim()) return;
	emit("confirm", reason.value);
}

// Each new banner starts empty, comes into view, and takes the keyboard focus.
watch(
	() => props.banner,
	async (banner) => {
		reason.value = "";
		if (!banner) return;
		await nextTick();
		root.value?.scrollIntoView({ block: "nearest", behavior: "smooth" });
		(reasonInput.value || confirmButton.value)?.focus({ preventScroll: true });
	}
);
</script>
