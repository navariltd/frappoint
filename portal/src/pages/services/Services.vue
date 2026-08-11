<template>
	<main
		class="max-w-7xl mx-auto px-gutter py-section-gap font-body-md text-on-surface antialiased"
	>
		<div class="flex flex-col lg:flex-row gap-8">
			<ServiceFilters
				:filters="filters"
				:categories="availableCategories"
				:priceBounds="priceRange"
				@toggleCategory="onToggleCategory"
				@clearCategories="onClearCategories"
				@duration="onDurationChange"
				@price="onPriceChange"
				@clear="clearFilters"
			/>

			<section class="flex-grow">
				<div
					class="sticky top-24 z-20 rounded-xl border border-outline-variant/20 bg-surface/90 backdrop-blur-md p-4 mb-6"
				>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
						<div>
							<label class="block text-[12px] text-on-surface-variant mb-1"
								>Search</label
							>
							<input
								type="text"
								:value="filters.search"
								placeholder="Search services"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-body-md text-on-surface"
								@input="onSearchChange($event.target.value)"
							/>
						</div>
						<div>
							<label class="block text-[12px] text-on-surface-variant mb-1"
								>Guests</label
							>
							<input
								type="number"
								min="1"
								:value="filters.guests"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-body-md text-on-surface"
								@input="onGuestsChange($event.target.value)"
							/>
						</div>
						<div>
							<label class="block text-[12px] text-on-surface-variant mb-1"
								>Date</label
							>
							<input
								type="date"
								:value="filters.date"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-body-md text-on-surface"
								@input="onDateChange($event.target.value)"
							/>
						</div>
					</div>
				</div>

				<ServiceFilterChips
					:filters="filters"
					@remove="removeFilterChip"
					@clear="clearFilters"
				/>

				<div
					v-if="error"
					class="rounded-lg border border-error-container bg-error-container/30 px-4 py-3 mb-6"
				>
					<p class="text-body-md text-on-surface">{{ error }}</p>
				</div>

				<ServiceSkeletonLoader v-if="loading" />
				<ServiceEmptyState v-else-if="!filteredServices.length" @clear="clearFilters" />
				<ServiceGrid
					v-else
					:services="filteredServices"
					@view="openService"
					@add="addToBooking"
				/>
				<Pagination
					v-if="!loading && pagination"
					:currentPage="pagination.page"
					:totalPages="pagination.total_pages"
					:hasNext="pagination.has_next"
					:hasPrevious="pagination.has_previous"
					@page-change="onPageChange"
				/>
			</section>
		</div>
	</main>
</template>

<script setup>
import { onMounted } from "vue";
import { useServices } from "@/composables/useServices";
import ServiceFilters from "@/components/services/ServiceFilters.vue";
import ServiceGrid from "@/components/services/ServiceGrid.vue";
import ServiceFilterChips from "@/components/services/ServiceFilterChips.vue";
import ServiceEmptyState from "@/components/services/ServiceEmptyState.vue";
import ServiceSkeletonLoader from "@/components/services/ServiceSkeletonLoader.vue";
import Pagination from "@/components/common/Pagination.vue";

const {
	filters,
	filteredServices,
	availableCategories,
	priceRange,
	loading,
	error,
	pagination,
	initialize,
	onSearchChange,
	onDateChange,
	onGuestsChange,
	onToggleCategory,
	onClearCategories,
	onDurationChange,
	onPriceChange,
	removeFilterChip,
	clearFilters,
	onPageChange,
	openService,
	addToBooking,
} = useServices();

onMounted(() => {
	initialize();
});
</script>
