<template>
	<div class="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6 animate-pulse">
		<div
			v-for="i in 6"
			:key="i"
			class="rounded-2xl border border-outline-variant p-6 space-y-3"
		>
			<div class="h-4 w-32 rounded bg-surface-variant"></div>
			<div class="h-5 w-48 rounded bg-surface-variant"></div>
			<div class="h-20 rounded bg-surface-variant"></div>
			<div class="h-16 rounded bg-surface-variant"></div>
		</div>
	</div>
</template>
