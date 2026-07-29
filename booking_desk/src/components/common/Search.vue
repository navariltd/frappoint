<template>
	<div class="flex-1 max-w-xl px-8">
		<div class="relative">
			<span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
				<span class="material-symbols-outlined text-text-sub-light text-lg">search</span>
			</span>
			<input
				class="block w-full pl-10 pr-12 py-[12px] sm:text-sm bg-surface-container-lowest border-border-light rounded-md focus:ring-secondary focus:border-secondary placeholder-text-sub-light text-text-main-light transition-colors"
				placeholder="Search"
				type="text"
			/>
			<div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
				<span
					class="text-xs text-text-sub-light border border-border-light rounded px-1.5 py-0.5"
					>⌘ K</span
				>
			</div>
		</div>
	</div>
</template>
