import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useCalendarStore } from "@/stores/calendar.store";

export function useCalendarWorkspace() {
	const store = useCalendarStore();
	const refs = storeToRefs(store);

	onMounted(() => {
		store.fetchEvents();
	});

	return {
		...refs,
		hasEvents: computed(() => store.hasEvents),
		visibleRange: computed(() => store.visibleRange),
		setView: store.setView,
		goToday: store.goToday,
		goPrev: store.goPrev,
		goNext: store.goNext,
		selectEvent: store.selectEvent,
		clearSelectedEvent: store.clearSelectedEvent,
		updateFilters: store.updateFilters,
		performAction: store.performAction,
		retry: store.retry,
	};
}
