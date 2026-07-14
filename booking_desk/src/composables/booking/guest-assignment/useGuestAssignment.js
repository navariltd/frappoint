import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useGuestAssignmentStore } from "@/stores/guestAssignment.store";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";
import { useServicesStore } from "@/stores/services.store";

export function useGuestAssignment() {
	const guestStore = useGuestAssignmentStore();
	const workflowStore = useBookingWorkflowStore();
	const servicesStore = useServicesStore();
	workflowStore.hydrateFromStorage();
	const {
		assignments,
		activeServiceIndex,
		activeGuestIndex,
		isLoadingDates,
		isLoadingSlots,
		isReservingSlots,
		reservingSlotIdByGuest,
		errorByGuest,
		progress,
		validationIssues,
		isComplete,
		summaryRows,
	} = storeToRefs(guestStore);
	const { cartItems, customers, selectedCustomerId, selectedCustomer, grandTotal } =
		storeToRefs(servicesStore);
	const { draftBooking, appointmentsByGuestKey } = storeToRefs(workflowStore);

	const sourceCartItems = computed(() => {
		return workflowStore.cartItemsSnapshot.length
			? workflowStore.cartItemsSnapshot
			: cartItems.value;
	});

	const workflowSelectedCustomerId = computed(() => {
		return workflowStore.customerSnapshot?.customer || selectedCustomerId.value;
	});

	const workflowSelectedCustomer = computed(() => {
		if (workflowStore.customerSnapshot?.customer) {
			return {
				id: workflowStore.customerSnapshot.customer,
				name:
					workflowStore.customerSnapshot.fullName ||
					workflowStore.customerSnapshot.name ||
					workflowStore.customerSnapshot.customer,
			};
		}

		return selectedCustomer.value || null;
	});

	const activeServiceKey = computed(
		() => assignments.value[activeServiceIndex.value]?.serviceKey || ""
	);

	const initialize = async () => {
		await servicesStore.loadCustomers();
		if (workflowStore.bookingId && workflowStore.hydrationRequiresRevalidation) {
			await workflowStore.reloadDraftBookingSession().catch(() => null);
		} else if (workflowStore.bookingId && !workflowStore.draftBooking.items.length) {
			await workflowStore.reloadDraftBookingSession().catch(() => null);
		}
		guestStore.initialize({
			cartItems: sourceCartItems.value,
			customers: customers.value,
			selectedCustomerId: workflowSelectedCustomerId.value,
			selectedCustomer: workflowSelectedCustomer.value,
			appointmentsByGuestKey: appointmentsByGuestKey.value,
		});
		await Promise.all(
			guestStore.assignments.map((service) =>
				guestStore.ensureServiceProviders(service.serviceKey).catch(() => [])
			)
		);
	};

	onMounted(initialize);

	return {
		assignments,
		activeServiceIndex,
		activeGuestIndex,
		activeServiceKey,
		isLoadingDates,
		isLoadingSlots,
		isReservingSlots,
		reservingSlotIdByGuest,
		errorByGuest,
		progress,
		validationIssues,
		isComplete,
		summaryRows,
		draftBooking,
		grandTotal,
		customers,
		setActiveIndices: guestStore.setActiveIndices,
		updateGuestFromCustomer: guestStore.updateGuestFromCustomer,
		quickCreateGuest: guestStore.quickCreateGuest,
		updateProviderPreference: guestStore.updateProviderPreference,
		updateGuestNotes: guestStore.updateGuestNotes,
		clearGuest: guestStore.clearGuest,
		fetchGuestDates: guestStore.fetchGuestDates,
		selectGuestDate: guestStore.selectGuestDate,
		selectGuestSlot: guestStore.selectGuestSlot,
		refresh: initialize,
	};
}
