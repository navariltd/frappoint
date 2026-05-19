<template>
	<div class="h-full flex flex-col animate-pulse">
		<div
			class="h-24 border-b border-outline-variant bg-surface-container-lowest px-4 py-4 space-y-2"
		>
			<div class="h-3 w-32 rounded bg-surface-variant"></div>
			<div class="h-5 w-56 rounded bg-surface-variant"></div>
			<div class="h-3 w-72 rounded bg-surface-variant"></div>
		</div>
		<div class="flex-1 min-h-0 flex overflow-hidden">
			<div
				class="hidden md:block w-72 lg:w-80 border-r border-outline-variant p-4 space-y-3"
			>
				<div class="h-3 w-28 rounded bg-surface-variant"></div>
				<div
					v-for="i in 3"
					:key="i"
					class="rounded-lg border border-outline-variant p-3 space-y-2"
				>
					<div class="h-3 w-24 rounded bg-surface-variant"></div>
					<div class="h-2 w-36 rounded bg-surface-variant"></div>
				</div>
			</div>
			<div class="flex-1 p-4 space-y-4">
				<div
					class="rounded-xl border border-outline-variant p-4 h-20 bg-surface-container"
				></div>
				<div
					class="rounded-xl border border-outline-variant p-4 h-14 bg-surface-container"
				></div>
				<div
					class="rounded-xl border border-outline-variant p-4 h-28 bg-surface-container"
				></div>
				<div
					class="rounded-xl border border-outline-variant p-4 h-28 bg-surface-container"
				></div>
			</div>
			<div
				class="hidden md:block w-80 lg:w-96 border-l border-outline-variant p-4 space-y-3"
			>
				<div class="h-3 w-32 rounded bg-surface-variant"></div>
				<div class="rounded-lg border border-outline-variant p-4 space-y-2">
					<div
						v-for="i in 5"
						:key="i"
						class="h-3 w-full rounded bg-surface-variant"
					></div>
				</div>
			</div>
		</div>
	</div>
</template>
