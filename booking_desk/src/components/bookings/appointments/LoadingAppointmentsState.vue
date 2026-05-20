<template>
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
		<div
			v-for="index in 8"
			:key="index"
			class="h-52 rounded-2xl border border-outline-variant/30 bg-surface-container-low animate-pulse"
		></div>
	</div>
</template>
