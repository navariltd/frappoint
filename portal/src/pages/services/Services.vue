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
		<div class="flex flex-col sm:flex-row gap-3 my-6 md:my-8">
			<!-- Search Bar -->
			<div class="relative flex-1">
				<FeatherIcon class="h-5 text-gray-500 absolute top-2.5 left-4" name="search" />
				<input
					v-model="searchQuery"
					class="w-full rounded-lg border-0 shadow-sm pl-12 pr-10 py-2.5 text-sm md:text-base focus:ring-2 focus:ring-primary/50 transition-shadow"
					type="text"
					placeholder="Search for a service..."
				/>
				<button
					v-if="searchQuery"
					@click="searchQuery = ''"
					class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 transition-colors"
				>
					<FeatherIcon class="h-5" name="x" />
				</button>
			</div>

			<!-- Category Filter Combobox -->
			<div class="sm:w-56 flex flex-col gap-1.5">
				<Combobox
					v-model="selectedCategory"
					:options="categoryOptions"
					placeholder="All Categories"
					variant="outline"
					class="sm:w-56 border-gray-300"
				>
					<template #prefix>
						<FeatherIcon class="h-4 text-primary" name="filter" />
					</template>
				</Combobox>
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

			<!-- Empty state -->
			<div
				v-if="!serviceTypesResource.loading && serviceTypes.length === 0"
				class="col-span-full flex flex-col items-center justify-center py-16 px-4"
			>
				<FeatherIcon class="h-16 w-16 text-gray-300 mb-4" name="search" />
				<h3 class="text-xl font-semibold text-gray-700 mb-2">No services found</h3>
				<p class="text-gray-500 text-center max-w-md">
					Try adjusting your search or filter to find what you're looking for.
				</p>
				<button
					v-if="searchQuery || selectedCategory"
					@click="clearFilters"
					class="mt-4 px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
				>
					Clear filters
				</button>
			</div>
		</div>

		<!-- Pagination Controls -->
		<Pagination
			v-if="!serviceTypesResource.loading && pagination"
			:current-page="currentPage"
			:total-pages="pagination.total_pages"
			:has-next="pagination.has_next"
			:has-previous="pagination.has_previous"
			@page-change="handlePageChange"
		/>

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
import Pagination from "@/components/common/Pagination.vue";
import { createResource, FeatherIcon, ErrorMessage, Combobox } from "frappe-ui";
import { computed, ref, watch } from "vue";

const searchQuery = ref("");
const selectedCategory = ref(null);
const debouncedSearchQuery = ref("");
const allCategories = ref([]); // Store categories from initial load
const currentPage = ref(1);
const pageSize = 12;
let debounceTimer = null;

// Client-side debouncing for search input
watch(searchQuery, (newValue) => {
	if (debounceTimer) {
		clearTimeout(debounceTimer);
	}

	debounceTimer = setTimeout(() => {
		debouncedSearchQuery.value = newValue;
		currentPage.value = 1; // Reset to first page on search
	}, 500); // 500ms debounce delay
});

const serviceTypesResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_types",
	method: "GET",
	auto: true,
	makeParams() {
		const params = {
			page: currentPage.value,
			page_size: pageSize,
		};

		// Only add search_term if it has a value
		if (debouncedSearchQuery.value && debouncedSearchQuery.value.trim()) {
			params.search_term = debouncedSearchQuery.value.trim();
		}

		// Only add item_group if a category is selected
		if (selectedCategory.value) {
			params.item_group = selectedCategory.value;
		}

		return params;
	},
	onSuccess(response) {
		// Extract and store categories only from initial unfiltered load
		if (!debouncedSearchQuery.value && !selectedCategory.value && response?.data) {
			const uniqueCategories = [
				...new Set(
					response.data.map((service) => service.item_group).filter((group) => group)
				),
			];
			allCategories.value = uniqueCategories.sort();
		}
	},
});

// Watch for changes and reload data, reset to page 1 when filters change
watch(selectedCategory, () => {
	currentPage.value = 1;
});

watch([debouncedSearchQuery, selectedCategory, currentPage], () => {
	serviceTypesResource.reload();
});

const serviceTypes = computed(() => {
	if (serviceTypesResource.data?.data) {
		return serviceTypesResource.data.data;
	}
	return [];
});

const pagination = computed(() => {
	if (serviceTypesResource.data?.pagination) {
		return serviceTypesResource.data.pagination;
	}
	return null;
});

// Use the stored categories (from initial load)
const categories = computed(() => allCategories.value);

// Format options for Combobox component
const categoryOptions = computed(() => {
	const options = [
		{ label: "All Categories", value: null },
		...allCategories.value.map((category) => ({
			label: category,
			value: category,
		})),
	];
	return options;
});

function clearFilters() {
	searchQuery.value = "";
	selectedCategory.value = null;
	currentPage.value = 1;
}

function handlePageChange(page) {
	currentPage.value = page;
	window.scrollTo({ top: 0, behavior: "smooth" });
}
</script>
