<template>
	<div class="my-4 w-full max-w-7xl mx-auto px-4 sm:px-6">
		<div class="mb-6 md:mb-10 max-w-3xl">
			<h2 class="text-2xl sm:text-3xl md:text-4xl font-black text-gray-900 mb-3 md:mb-4">
				Select a Service
			</h2>
			<p class="text-base sm:text-lg text-gray-500 leading-relaxed">
				Choose from our curated range of professional treatments designed for your ultimate
				relaxation and well-being
			</p>
		</div>

		<!-- Search section  -->
		<div
			class="flex flex-col md:flex-row md:justify-between md:items-center gap-4 my-6 md:my-8"
		>
			<!-- Search Bar -->
			<div class="relative w-full md:w-auto md:flex-1 md:max-w-md">
				<FeatherIcon class="h-5 text-gray-500 absolute top-2.5 left-4" name="search" />
				<input
					class="w-full rounded-lg border-0 shadow-sm pl-12 pr-4 py-2.5 text-sm md:text-base"
					type="search"
					placeholder="Search for a service..."
				/>
			</div>

			<!-- Filter Buttons -->
			<div
				class="flex gap-2 md:gap-3 items-center overflow-x-auto pb-2 md:pb-0 scrollbar-hide"
			>
				<span
					class="px-4 sm:px-5 md:px-6 py-2 rounded-full text-white bg-primary whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-primary/90 transition-colors"
					>All</span
				>
				<span
					class="px-4 sm:px-5 md:px-6 py-2 rounded-full text-gray-700 bg-white whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-gray-50 transition-colors shadow-sm"
					>Hair</span
				>
				<span
					class="px-4 sm:px-5 md:px-6 py-2 rounded-full text-gray-700 bg-white whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-gray-50 transition-colors shadow-sm"
					>Spa</span
				>
				<span
					class="px-4 sm:px-5 md:px-6 py-2 rounded-full text-gray-700 bg-white whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-gray-50 transition-colors shadow-sm"
					>Nails</span
				>
				<span
					class="px-4 sm:px-5 md:px-6 py-2 rounded-full text-gray-700 bg-white whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-gray-50 transition-colors shadow-sm"
					>Facial</span
				>
			</div>
		</div>

		<!-- Services Grid -->
		<div
			class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 md:gap-8"
		>
			<!-- Show skeletons while loading -->
			<template v-if="serviceTypesResource.loading">
				<ServiceCardSkeleton v-for="n in 8" :key="n" />
			</template>

			<!-- Show actual service cards when loaded -->
			<template v-else>
				<ServiceCard
					v-for="serviceType in serviceTypes"
					:key="serviceType.name"
					:serviceType="serviceType"
				/>
			</template>
		</div>

		<ErrorMessage
			v-if="serviceTypesResource.error"
			:message="serviceTypesResource.error"
			class="mb-6"
		/>
	</div>
</template>

<script setup>
import ServiceCard from "@/components/services/ServiceCard.vue";
import ServiceCardSkeleton from "@/components/services/ServiceCardSkeleton.vue";
import { createResource, FeatherIcon, ErrorMessage } from "frappe-ui";
import { computed } from "vue";

const serviceTypesResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	method: "GET",
	auto: true,
	// cache: serviceTypesResource
});

const serviceTypes = computed(() => {
	if (serviceTypesResource.data) {
		return serviceTypesResource.data;
	}
	return [];
});
</script>
