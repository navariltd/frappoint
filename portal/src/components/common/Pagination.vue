<template>
	<div v-if="totalPages > 1" class="mt-10 flex items-center justify-center gap-2 pb-6">
		<!-- Previous button -->
		<button
			type="button"
			@click="goToPrevious"
			:disabled="!hasPrevious"
			:class="[
				hasPrevious
					? 'bg-surface-light text-on-surface hover:bg-surface-container-high hover:border-outline'
					: 'bg-surface-container-low text-on-surface-variant/50 cursor-not-allowed border-outline-variant/50',
				'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all flex items-center gap-2 shadow-sm',
			]"
		>
			<FeatherIcon class="h-4" name="chevron-left" />
			<span class="hidden sm:inline">Previous</span>
		</button>

		<!-- Page numbers -->
		<div class="flex items-center gap-1.5">
			<button
				v-for="page in pageNumbers"
				:key="page"
				type="button"
				@click="page !== '...' && goToPage(page)"
				:class="[
					page === currentPage
						? 'bg-primary text-on-primary border-primary shadow-sm'
						: page === '...'
						? 'cursor-default text-on-surface-variant border-transparent bg-transparent'
						: 'bg-surface-light text-on-surface hover:bg-surface-container-high hover:border-outline border-outline-variant',
					'px-3.5 py-2.5 rounded-lg border text-sm font-medium transition-all min-w-[42px] shadow-sm',
				]"
				:disabled="page === '...'"
				:aria-current="page === currentPage ? 'page' : undefined"
			>
				{{ page }}
			</button>
		</div>

		<!-- Next button -->
		<button
			type="button"
			@click="goToNext"
			:disabled="!hasNext"
			:class="[
				hasNext
					? 'bg-surface-light text-on-surface hover:bg-surface-container-high hover:border-outline'
					: 'bg-surface-container-low text-on-surface-variant/50 cursor-not-allowed border-outline-variant/50',
				'px-4 py-2.5 rounded-lg border text-sm font-medium transition-all flex items-center gap-2 shadow-sm',
			]"
		>
			<span class="hidden sm:inline">Next</span>
			<FeatherIcon class="h-4" name="chevron-right" />
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { FeatherIcon } from "frappe-ui";

const props = defineProps({
	currentPage: {
		type: Number,
		required: true,
		default: 1,
	},
	totalPages: {
		type: Number,
		required: true,
		default: 1,
	},
	hasNext: {
		type: Boolean,
		default: false,
	},
	hasPrevious: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["page-change"]);

const pageNumbers = computed(() => {
	const total = props.totalPages;
	const current = props.currentPage;
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
});

function goToPage(page) {
	if (page !== props.currentPage && page !== "...") {
		emit("page-change", page);
	}
}

function goToNext() {
	if (props.hasNext) {
		emit("page-change", props.currentPage + 1);
	}
}

function goToPrevious() {
	if (props.hasPrevious) {
		emit("page-change", props.currentPage - 1);
	}
}
</script>
