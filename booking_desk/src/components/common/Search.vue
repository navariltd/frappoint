<template>
	<div class="flex-1 max-w-xl px-8">
		<div class="relative">
			<span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
				<span
					class="material-symbols-outlined text-text-sub-light dark:text-text-sub-dark text-lg"
					>search</span
				>
			</span>
			<input
				class="block w-full pl-10 pr-12 py-[12px] sm:text-sm bg-gray-50 dark:bg-gray-800 border-border-light dark:border-border-dark rounded-md focus:ring-primary focus:border-primary placeholder-text-sub-light dark:placeholder-text-sub-dark text-text-main-light dark:text-text-main-dark transition-colors"
				placeholder="Search"
				type="text"
			/>
			<div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
				<span
					class="text-xs text-text-sub-light dark:text-text-sub-dark border border-border-light dark:border-border-dark rounded px-1.5 py-0.5"
					>⌘ K</span
				>
			</div>
		</div>
	</div>
</template>
