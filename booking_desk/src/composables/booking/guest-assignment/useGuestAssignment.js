import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useGuestAssignmentStore } from "@/stores/guestAssignment.store";
import { useServicesStore } from "@/stores/services.store";

export function useGuestAssignment() {
	const guestStore = useGuestAssignmentStore();
	const servicesStore = useServicesStore();
	const {
		assignments,
		activeServiceIndex,
		activeGuestIndex,
		isLoadingDates,
		isLoadingSlots,
		errorByGuest,
		progress,
		validationIssues,
		isComplete,
		summaryRows,
	} = storeToRefs(guestStore);
	const { cartItems, customers, selectedCustomerId, grandTotal } = storeToRefs(servicesStore);

	const activeServiceKey = computed(
		() => assignments.value[activeServiceIndex.value]?.serviceKey || ""
	);

	const initialize = async () => {
		if (!customers.value.length) {
			await servicesStore.loadCustomers();
		}
		guestStore.initialize({
			cartItems: cartItems.value,
			customers: customers.value,
			selectedCustomerId: selectedCustomerId.value,
		});
	};

	onMounted(initialize);

	return {
		assignments,
		activeServiceIndex,
		activeGuestIndex,
		activeServiceKey,
		isLoadingDates,
		isLoadingSlots,
		errorByGuest,
		progress,
		validationIssues,
		isComplete,
		summaryRows,
		grandTotal,
		customers,
		setActiveIndices: guestStore.setActiveIndices,
		updateGuestFromCustomer: guestStore.updateGuestFromCustomer,
		quickCreateGuest: guestStore.quickCreateGuest,
		clearGuest: guestStore.clearGuest,
		fetchGuestDates: guestStore.fetchGuestDates,
		selectGuestDate: guestStore.selectGuestDate,
		selectGuestSlot: guestStore.selectGuestSlot,
		refresh: initialize,
	};
}
