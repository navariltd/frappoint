import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useBookingWorkflowStore } from "@/stores/bookingWorkflow.store";
import { useBookingCart } from "./useBookingCart";
import { useAuthStore } from "@/stores/auth";
import { resolveLoggedInCustomerProfile } from "@/services/bookingWorkflow.service";

export function useBookingWorkflow() {
	const store = useBookingWorkflowStore();
	const cart = useBookingCart();
	const auth = useAuthStore();

	store.hydrateFromStorage();

	const {
		draftBooking,
		assignments,
		activeAssignmentIndex,
		isCreatingBooking,
		bookingError,
		assignmentErrors,
		isLoadingDatesByAssignment,
		isLoadingSlotsByAssignment,
		isSavingAssignmentById,
	} = storeToRefs(store);

	const activeAssignment = computed(() => store.activeAssignment);
	const totalGuests = computed(() => store.totalGuests);
	const completedAssignments = computed(() => store.completedAssignments);
	const pendingAssignments = computed(() => store.pendingAssignments);
	const progressPercentage = computed(() => store.progressPercentage);
	const isWorkflowComplete = computed(() => store.isWorkflowComplete);

	const assignmentsByService = computed(() => {
		const grouped = new Map<string, typeof assignments.value>();
		for (const assignment of assignments.value) {
			const key = assignment.service_key;
			if (!grouped.has(key)) grouped.set(key, []);
			grouped.get(key)!.push(assignment);
		}
		return grouped;
	});

	async function startWorkflow() {
		if (!auth.isLoggedIn) {
			throw new Error("Must be authenticated to continue booking.");
		}

		const customerProfile = await resolveLoggedInCustomerProfile();
		if (!customerProfile?.customer) {
			throw new Error(
				"Your portal account is not linked to a customer profile. Please contact support."
			);
		}

		if (!store.assignments.length || !store.draftBooking) {
			const items = cart.cartItems.value;
			if (!items.length) throw new Error("Your booking cart is empty.");
			store.initializeFromCart(items);
		}

		// Recover from stale persisted workflow linked to a wrong/non-customer identity.
		if (
			store.draftBooking?.id &&
			store.draftBooking.customer &&
			store.draftBooking.customer !== customerProfile.customer
		) {
			const items = cart.cartItems.value;
			store.clearWorkflow();
			if (!items.length) throw new Error("Your booking cart is empty.");
			store.initializeFromCart(items);
		}

		if (!store.draftBooking?.id) {
			await store.createDraftBooking({
				customer: customerProfile.customer,
				fullName: customerProfile.contact?.contact_display || auth.userName || "",
				email: customerProfile.contact?.contact_email || "",
				mobileNo: customerProfile.contact?.contact_phone || "",
			});
		}
	}

	function setActiveAssignment(index: number) {
		store.setActiveAssignment(index);
	}

	function assignGuest(assignmentId: string, payload: { fullName: string; email?: string; mobile?: string }) {
		store.assignGuest(assignmentId, payload);
	}

	async function loadDates(assignmentId: string) {
		return store.fetchAvailableDates(assignmentId);
	}

	async function chooseDate(assignmentId: string, date: string) {
		store.selectDate(assignmentId, date);
		return store.fetchAvailableSlots(assignmentId);
	}

	async function loadSlots(assignmentId: string) {
		return store.fetchAvailableSlots(assignmentId);
	}

	function chooseSlot(assignmentId: string, slotId: string) {
		store.selectSlot(assignmentId, slotId);
	}

	async function confirmAssignment(assignmentId: string) {
		const issues = store.validateAssignment(assignmentId);
		if (issues.length) {
			store.setAssignmentError(assignmentId, issues[0]);
			throw new Error(issues[0]);
		}
		return store.createDraftAppointment(assignmentId);
	}

	function getAssignmentError(assignmentId: string) {
		return assignmentErrors.value[assignmentId] || "";
	}

	function isLoadingDates(assignmentId: string) {
		return Boolean(isLoadingDatesByAssignment.value[assignmentId]);
	}

	function isLoadingSlots(assignmentId: string) {
		return Boolean(isLoadingSlotsByAssignment.value[assignmentId]);
	}

	function isSavingAssignment(assignmentId: string) {
		return Boolean(isSavingAssignmentById.value[assignmentId]);
	}

	return {
		draftBooking,
		assignments,
		activeAssignment,
		activeAssignmentIndex,
		isCreatingBooking,
		bookingError,
		assignmentErrors,
		totalGuests,
		completedAssignments,
		pendingAssignments,
		progressPercentage,
		isWorkflowComplete,
		assignmentsByService,
		startWorkflow,
		setActiveAssignment,
		assignGuest,
		loadDates,
		chooseDate,
		loadSlots,
		chooseSlot,
		confirmAssignment,
		getAssignmentError,
		isLoadingDates,
		isLoadingSlots,
		isSavingAssignment,
		clearWorkflow: store.clearWorkflow,
	};
}
