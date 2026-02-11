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

			<!-- Filter Buttons -->
			<div
				class="flex gap-2 md:gap-3 items-center overflow-x-auto pb-2 md:pb-0 scrollbar-hide"
			>
				<span
					@click="selectedCategory = null"
					:class="[
						selectedCategory === null
							? 'text-white bg-primary'
							: 'text-gray-700 bg-white shadow-sm',
						'px-4 sm:px-5 md:px-6 py-2 rounded-full whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-primary/90 hover:text-white transition-colors',
					]"
					>All</span
				>
				<span
					v-for="category in categories"
					:key="category"
					@click="selectedCategory = category"
					:class="[
						selectedCategory === category
							? 'text-white bg-primary'
							: 'text-gray-700 bg-white shadow-sm',
						'px-4 sm:px-5 md:px-6 py-2 rounded-full whitespace-nowrap text-sm md:text-base cursor-pointer hover:bg-primary/90 hover:text-white transition-colors',
					]"
					>{{ category }}</span
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
		<div
			v-if="!serviceTypesResource.loading && pagination && pagination.total_pages > 1"
			class="mt-10 flex items-center justify-center gap-2 pb-6"
		>
			<!-- Pagination buttons -->
			<button
				@click="previousPage"
				:disabled="!pagination.has_previous"
				:class="[
					pagination.has_previous
						? 'bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400'
						: 'bg-gray-50 text-gray-400 cursor-not-allowed border-gray-200',
					'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all flex items-center gap-2 shadow-sm',
				]"
			>
				<FeatherIcon class="h-4" name="chevron-left" />
				<span class="hidden sm:inline">Previous</span>
			</button>

			<!-- Page numbers -->
			<div class="flex items-center gap-1.5">
				<button
					v-for="page in getPageNumbers()"
					:key="page"
					@click="page !== '...' && goToPage(page)"
					:class="[
						page === currentPage
							? 'bg-primary text-white border-primary shadow-sm'
							: page === '...'
							? 'cursor-default text-gray-400 border-transparent bg-transparent'
							: 'bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400 border-gray-300',
						'px-3.5 py-2.5 rounded-lg border text-sm font-medium transition-all min-w-[42px] shadow-sm',
					]"
					:disabled="page === '...'"
				>
					{{ page }}
				</button>
			</div>

			<button
				@click="nextPage"
				:disabled="!pagination.has_next"
				:class="[
					pagination.has_next
						? 'bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400'
						: 'bg-gray-50 text-gray-400 cursor-not-allowed border-gray-200',
					'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all flex items-center gap-2 shadow-sm',
				]"
			>
				<span class="hidden sm:inline">Next</span>
				<FeatherIcon class="h-4" name="chevron-right" />
			</button>
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

function clearFilters() {
	searchQuery.value = "";
	selectedCategory.value = null;
	currentPage.value = 1;
}

function goToPage(page) {
	currentPage.value = page;
	window.scrollTo({ top: 0, behavior: "smooth" });
}

function nextPage() {
	if (pagination.value?.has_next) {
		currentPage.value++;
		window.scrollTo({ top: 0, behavior: "smooth" });
	}
}

function previousPage() {
	if (pagination.value?.has_previous) {
		currentPage.value--;
		window.scrollTo({ top: 0, behavior: "smooth" });
	}
}

function getPageNumbers() {
	if (!pagination.value) return [];

	const total = pagination.value.total_pages;
	const current = pagination.value.page;
	const pages = [];

	// Always show first page
	pages.push(1);

	if (total <= 7) {
		// Show all pages if total is 7 or less
		for (let i = 2; i <= total; i++) {
			pages.push(i);
		}
	} else {
		// Show smart pagination with ellipsis
		if (current <= 3) {
			// Near the start
			for (let i = 2; i <= 4; i++) {
				pages.push(i);
			}
			pages.push("...");
			pages.push(total);
		} else if (current >= total - 2) {
			// Near the end
			pages.push("...");
			for (let i = total - 3; i <= total; i++) {
				pages.push(i);
			}
		} else {
			// In the middle
			pages.push("...");
			for (let i = current - 1; i <= current + 1; i++) {
				pages.push(i);
			}
			pages.push("...");
			pages.push(total);
		}
	}

	return pages;
}
</script>
