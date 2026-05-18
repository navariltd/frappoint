import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard.store";

export function useDashboard() {
	const store = useDashboardStore();
	const { metrics, isLoading, error } = storeToRefs(store);

	const summaryCards = computed(() => [
		{
			key: "todayAppointments",
			label: "Today's Appt",
			number: metrics.value.todayAppointments,
			icon: "calendar_add_on",
		},
		{
			key: "checkedIn",
			label: "Checked-In",
			number: metrics.value.checkedIn,
			icon: "check_circle",
		},
		{
			key: "ongoing",
			label: "Ongoing",
			number: metrics.value.ongoing,
			icon: "sync",
		},
		{
			key: "pendingPayment",
			label: "Pending Payment",
			number: metrics.value.pendingPayment,
			icon: "pending",
			numberColor: "text-tertiary",
			iconColor: "text-tertiary",
		},
		{
			key: "delayed",
			label: "Delayed",
			number: metrics.value.delayed,
			icon: "warning",
			numberColor: "text-error",
			iconColor: "text-error",
			borderLeftColor: "border-l-error",
			iconFilled: true,
		},
		{
			key: "noShow",
			label: "No-Show",
			number: metrics.value.noShow,
			icon: "person_off",
			numberColor: "text-on-surface-variant",
			iconColor: "text-on-surface-variant",
			numberOpacity: "opacity-50",
			iconOpacity: "opacity-30",
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
