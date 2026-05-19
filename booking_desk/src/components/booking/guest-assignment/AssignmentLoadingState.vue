<template>
	<div class="space-y-3">
		<div v-for="index in 3" :key="index" class="rounded-xl border border-outline-variant p-4">
			<div class="h-4 w-48 animate-pulse rounded bg-surface-variant"></div>
			<div class="mt-3 h-3 w-full animate-pulse rounded bg-surface-variant"></div>
			<div class="mt-2 h-3 w-5/6 animate-pulse rounded bg-surface-variant"></div>
		</div>
	</div>
</template>
