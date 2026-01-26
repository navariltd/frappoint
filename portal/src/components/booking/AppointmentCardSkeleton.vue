<template>
	<div
		class="flex items-start gap-2 sm:gap-4 rounded-lg sm:rounded-xl shadow-sm p-3 sm:p-5 bg-white animate-pulse"
	>
		<!-- Date Badge Skeleton -->
		<div
			class="flex flex-col items-center justify-center min-w-[45px] sm:min-w-[60px] flex-shrink-0"
		>
			<div class="h-3 sm:h-4 bg-gray-200 rounded w-8 mb-1"></div>
			<div class="h-6 sm:h-8 bg-gray-200 rounded w-10 mb-1"></div>
			<div class="h-3 bg-gray-200 rounded w-12"></div>
		</div>

		<!-- Appointment Details Skeleton -->
		<div class="flex-1 min-w-0">
			<!-- Service Name -->
			<div class="h-5 sm:h-6 bg-gray-200 rounded w-3/4 mb-2"></div>

			<!-- Provider Info -->
			<div class="flex items-center gap-2 mb-2">
				<div class="size-6 sm:size-8 bg-gray-200 rounded-full"></div>
				<div class="h-4 bg-gray-200 rounded w-32"></div>
			</div>

			<!-- Additional info for next up variant -->
			<div class="flex gap-4 mt-2">
				<div class="h-3 bg-gray-200 rounded w-20"></div>
				<div class="h-3 bg-gray-200 rounded w-20"></div>
			</div>
		</div>

		<!-- Actions Skeleton -->
		<div class="flex items-center gap-2 flex-shrink-0">
			<div class="h-8 w-8 bg-gray-200 rounded-lg"></div>
		</div>
	</div>
</template>

<script setup>
// Skeleton component for loading state
</script>
