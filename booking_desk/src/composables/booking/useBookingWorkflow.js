import { storeToRefs } from "pinia";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";

export function useBookingWorkflow() {
	const store = useBookingWorkflowStore();
	store.hydrateFromStorage();
	if (store.hydrationRequiresRevalidation && store.bookingId && !store.isHydratingBooking) {
		store.reloadDraftBookingSession().catch(() => store.clearWorkflow());
	}

	const {
		draftBooking,
		isCreatingBooking,
		isHydratingBooking,
		bookingError,
		appointmentsByGuestKey,
	} = storeToRefs(store);

	return {
		draftBooking,
		isCreatingBooking,
		isHydratingBooking,
		bookingError,
		appointmentsByGuestKey,
		hasDraftBooking: store.hasDraftBooking,
		bookingId: store.bookingId,
		cartItemsSnapshot: store.cartItemsSnapshot,
		customerSnapshot: store.customerSnapshot,
		createDraftBookingSession: store.createDraftBookingSession,
		reloadDraftBookingSession: store.reloadDraftBookingSession,
		clearBookingError: store.clearBookingError,
		clearWorkflow: store.clearWorkflow,
	};
}
