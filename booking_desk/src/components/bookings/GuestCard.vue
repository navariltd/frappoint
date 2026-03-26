<template>
	<div
		class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 flex items-start gap-5 shadow-sm hover:shadow-md transition-all group relative"
	>
		<div
			v-if="isIncomplete"
			class="absolute -top-2 -left-2 z-10 bg-rose-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-lg flex items-center gap-1 animate-bounce"
		>
			<span class="material-symbols-outlined text-[12px]">warning</span>
			Incomplete
		</div>

		<div class="relative shrink-0">
			<img
				class="size-14 rounded-xl object-cover border border-slate-100 dark:border-slate-800"
				:src="
					guest.image || 'https://ui-avatars.com/api/?name=' + (guest.full_name || 'G')
				"
				:alt="guest.full_name"
			/>
		</div>

		<div class="flex-1 min-w-0">
			<div class="flex justify-between items-start gap-4">
				<div class="min-w-0">
					<h4 class="font-bold text-slate-900 dark:text-white text-lg truncate">
						{{ guest.guest_full_name || "New Guest" }}
					</h4>

					<div class="flex items-center flex-wrap gap-2 mt-1">
						<span
							v-if="guest.appointment_type"
							class="bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide"
						>
							{{ guest.appointment_type }}
						</span>
						<span
							v-else
							class="bg-rose-50 dark:bg-rose-900/20 text-rose-500 text-[10px] font-bold px-2 py-0.5 rounded uppercase italic"
						>
							Select Service
						</span>

						<span
							v-if="guest.duration"
							class="text-slate-300 dark:text-slate-700 text-xs"
							>•</span
						>
						<span v-if="guest.duration" class="text-slate-500 text-sm font-medium"
							>{{ guest.duration }} min</span
						>
					</div>
				</div>

				<div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
					<button
						@click="$emit('edit', guest)"
						class="p-2 text-slate-400 hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
					>
						<span class="material-symbols-outlined text-[20px]">edit</span>
					</button>
					<button
						@click="$emit('remove', guest.id)"
						class="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
					>
						<span class="material-symbols-outlined text-[20px]">delete</span>
					</button>
				</div>
			</div>

			<div
				v-if="guest.provider || guest.slot"
				class="mt-4 flex flex-wrap gap-6 items-center border-t border-slate-50 dark:border-slate-800 pt-4"
			>
				<div v-if="guest.provider" class="flex items-center gap-2">
					<span class="material-symbols-outlined text-[18px] text-slate-400"
						>person</span
					>
					<span class="text-sm text-slate-600 dark:text-slate-400"
						>Provider:
						<span class="font-semibold text-slate-900 dark:text-white">{{
							guest.provider
						}}</span>
					</span>
				</div>

				<div v-if="guest.slot" class="flex items-center gap-2">
					<span class="material-symbols-outlined text-[18px] text-slate-400"
						>calendar_month</span
					>
					<span class="text-sm text-slate-600 dark:text-slate-400">
						<span class="font-semibold text-slate-900 dark:text-white">{{
							guest.date
						}}</span>
						at
						<span class="font-semibold text-slate-900 dark:text-white">
							{{
								typeof guest.slot === "object" ? guest.slot.start_time : guest.slot
							}}
						</span>
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	guest: {
		type: Object,
		required: true,
	},
});

defineEmits(["edit", "remove"]);

// Validation logic to check if the guest has the bare essentials
const isIncomplete = computed(() => {
	return !props.guest.guest_full_name || !props.guest.appointment_type || !props.guest.slot;
});
</script>
