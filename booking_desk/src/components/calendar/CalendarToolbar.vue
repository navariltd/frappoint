<template>
	<section
		class="bg-surface-container-lowest px-4 py-3 border border-outline-variant/20 rounded-xl flex flex-col gap-3"
	>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-center gap-3">
				<div class="flex items-center bg-surface-container-low rounded-lg p-1">
					<button
						class="p-1 hover:bg-surface-container-highest rounded transition-colors"
						@click="$emit('prev')"
					>
						<span class="material-symbols-outlined text-[18px]">chevron_left</span>
					</button>
					<button
						class="px-3 py-1 text-[12px] font-semibold hover:bg-surface-container-highest rounded transition-colors"
						@click="$emit('today')"
					>
						Today
					</button>
					<button
						class="p-1 hover:bg-surface-container-highest rounded transition-colors"
						@click="$emit('next')"
					>
						<span class="material-symbols-outlined text-[18px]">chevron_right</span>
					</button>
				</div>
				<h2 class="text-[14px] font-semibold text-on-surface">{{ rangeLabel }}</h2>
			</div>
			<div class="flex bg-surface-container-low rounded-lg p-1">
				<button
					v-for="view in views"
					:key="view.value"
					class="px-4 py-1 text-[12px] rounded-md transition-colors"
					:class="
						activeView === view.value
							? 'bg-surface-container-lowest text-primary font-semibold shadow-sm'
							: 'text-on-surface-variant hover:text-primary'
					"
					@click="$emit('changeView', view.value)"
				>
					{{ view.label }}
				</button>
			</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2">
			<select
				:value="filters.provider"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@change="$emit('update:provider', $event.target.value)"
			>
				<option value="">All Providers</option>
				<option v-for="option in providerOptions" :key="option" :value="option">
					{{ option }}
				</option>
			</select>
			<select
				:value="filters.resource"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@change="$emit('update:resource', $event.target.value)"
			>
				<option value="">All Resources</option>
				<option v-for="option in resourceOptions" :key="option" :value="option">
					{{ option }}
				</option>
			</select>
			<select
				:value="filters.statuses[0] || ''"
				class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[13px]"
				@change="$emit('update:status', $event.target.value)"
			>
				<option value="">All Statuses</option>
				<option v-for="option in statusOptions" :key="option" :value="option">
					{{ option }}
				</option>
			</select>
		</div>
	</section>
</template>

<script setup>
defineProps({
	activeView: { type: String, default: "week" },
	rangeLabel: { type: String, default: "" },
	filters: { type: Object, required: true },
	providerOptions: { type: Array, default: () => [] },
	resourceOptions: { type: Array, default: () => [] },
	statusOptions: { type: Array, default: () => [] },
});

const views = [
	{ value: "day", label: "Day" },
	{ value: "week", label: "Week" },
	{ value: "month", label: "Month" },
];

defineEmits([
	"prev",
	"next",
	"today",
	"changeView",
	"update:provider",
	"update:resource",
	"update:status",
]);
</script>
