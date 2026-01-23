<template>
	<div
		class="bg-surface-light rounded-2xl overflow-hidden border border-gray-100 shadow-[0_2px_12px_rgba(0,0,0,0.04)] flex-col justify-center animate-pulse"
	>
		<!-- Image skeleton -->
		<div class="relative h-48 bg-gray-200"></div>

		<div class="p-5 flex flex-col flex-grow">
			<!-- Title skeleton -->
			<div class="h-7 bg-gray-200 rounded-md w-3/4 mb-3"></div>

			<!-- Description skeleton -->
			<div class="space-y-2 mb-6">
				<div class="h-4 bg-gray-200 rounded w-full"></div>
				<div class="h-4 bg-gray-200 rounded w-5/6"></div>
			</div>

			<!-- Footer skeleton -->
			<div class="mt-auto pt-4 border-t border-gray-100 flex items-center justify-between">
				<div class="flex flex-col gap-2">
					<div class="h-3 bg-gray-200 rounded w-12"></div>
					<div class="h-5 bg-gray-200 rounded w-16"></div>
				</div>

				<div class="h-7 w-16 bg-gray-200 rounded-md"></div>
			</div>

			<!-- Button skeleton -->
			<div class="mt-4 w-full h-12 bg-gray-200 rounded-xl"></div>
		</div>
	</div>
</template>

<script setup></script>
