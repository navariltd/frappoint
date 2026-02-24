<template>
	<div class="w-full flex flex-col lg:flex-row animate-pulse">
		<!-- LEFT COLUMN: Calendar Skeleton -->
		<div
			class="w-full lg:w-6/12 p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-gray-100 bg-white"
		>
			<!-- Month header -->
			<div class="flex items-center justify-between mb-6">
				<div class="h-6 w-24 bg-gray-200 rounded"></div>
				<div class="flex gap-2">
					<div class="h-6 w-6 bg-gray-200 rounded"></div>
					<div class="h-6 w-6 bg-gray-200 rounded"></div>
				</div>
			</div>

			<!-- Day names -->
			<div class="grid grid-cols-7 gap-2 mb-4">
				<div v-for="i in 7" :key="`day-${i}`" class="h-8 bg-gray-100 rounded"></div>
			</div>

			<!-- Calendar dates grid -->
			<div class="grid grid-cols-7 gap-2">
				<div v-for="i in 35" :key="`date-${i}`" class="h-12 bg-gray-100 rounded"></div>
			</div>
		</div>

		<!-- RIGHT COLUMN: Time Slots Skeleton -->
		<div class="w-full lg:w-7/12 p-6 md:p-8 bg-gray-50">
			<!-- Provider dropdown skeleton -->
			<div class="mb-6">
				<div class="h-4 w-48 bg-gray-200 rounded mb-2"></div>
				<div class="h-12 w-full bg-white border border-gray-200 rounded-lg"></div>
			</div>

			<!-- Selected date header -->
			<div class="h-6 w-40 bg-gray-200 rounded mb-4"></div>

			<!-- Time slots grid -->
			<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
				<div
					v-for="i in 12"
					:key="`slot-${i}`"
					class="h-14 bg-white border border-gray-200 rounded-lg"
				></div>
			</div>
		</div>
	</div>
</template>

<script setup>
// No props or logic needed for a pure skeleton component
</script>
