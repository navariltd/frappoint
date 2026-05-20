import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard.store";

export function useDashboard() {
	const store = useDashboardStore();
	const { metrics, isLoading, error } = storeToRefs(store);

	const summaryCards = computed(() => [
		{
			key: "todayAppointments",
			label: "Today's Appointments",
			number: metrics.value.todayAppointments,
			icon: "calendar_add_on",
		},
		{
			key: "checkedIn",
			label: "Checked In",
			number: metrics.value.checkedIn,
			icon: "check_circle",
			numberColor: "text-secondary",
			iconColor: "text-secondary",
		},
		{
			key: "inProgress",
			label: "In Progress",
			number: metrics.value.ongoing,
			icon: "hourglass_top",
			numberColor: "text-primary",
			iconColor: "text-primary",
		},
		{
			key: "completed",
			label: "Completed",
			number: metrics.value.completed,
			icon: "task_alt",
			numberColor: "text-secondary",
			iconColor: "text-secondary",
		},
		{
			key: "pendingPayment",
			label: "Pending Payments",
			number: metrics.value.pendingPayment,
			icon: "pending",
			numberColor: "text-tertiary",
			iconColor: "text-tertiary",
		},
		{
			key: "cancelled",
			label: "Cancelled",
			number: metrics.value.cancelled,
			icon: "event_busy",
			numberColor: "text-error",
			iconColor: "text-error",
		},
		{
			key: "delayed",
			label: "Delayed",
			number: metrics.value.delayed,
			icon: "running_with_errors",
			numberColor: "text-error",
			iconColor: "text-error",
		},
		{
			key: "noShow",
			label: "No-Show",
			number: metrics.value.noShow,
			icon: "person_off",
			numberColor: "text-on-surface-variant",
			iconColor: "text-on-surface-variant",
		},
	]);

	const retry = () => store.refresh({ force: true });

	onMounted(() => {
		store.refresh();
	});

	return {
		summaryCards,
		isLoading,
		error,
		retry,
	};
}
