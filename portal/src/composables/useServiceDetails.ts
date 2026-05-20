import { computed, onBeforeUnmount, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useBookingStore } from "@/stores/bookingStore";
import { useServiceDetailsStore } from "@/stores/serviceDetails.store";

export function useServiceDetails() {
	const route = useRoute();
	const router = useRouter();
	const bookingStore = useBookingStore();
	const serviceDetailsStore = useServiceDetailsStore();
	const {
		serviceDetails,
		loading,
		error,
		packages,
		selectedPackage,
		formattedBenefits,
		formattedTechniques,
	} = storeToRefs(serviceDetailsStore);

	const serviceType = computed(() => {
		const name = route.params.name;
		return Array.isArray(name) ? name[0] : name || "";
	});

	const longDescription = computed(() => {
		return serviceDetails.value?.long_description || serviceDetails.value?.description || "";
	});

	const isAddingToBooking = ref(false);
	const bookingError = ref("");

	async function refreshServiceDetails() {
		if (!serviceType.value) {
			serviceDetailsStore.clearServiceDetails();
			return null;
		}

		return serviceDetailsStore.fetchServiceDetails(serviceType.value);
	}

	function selectPackage(packageItem) {
		serviceDetailsStore.setSelectedPackage(packageItem);
	}

	async function handleAddToBooking() {
		const service = serviceDetails.value;
		const selectedPrice = selectedPackage.value;

		bookingError.value = "";

		if (!service || !selectedPrice || isAddingToBooking.value) {
			return;
		}

		isAddingToBooking.value = true;

		try {
			bookingStore.setServiceType(service.name || service.appointment_type || serviceType.value);
			bookingStore.setDuration(selectedPrice.duration || null);
			bookingStore.setPriceName(selectedPrice.price_name || null);
			bookingStore.setPrice(selectedPrice.amount || null);
			bookingStore.setCurrency(selectedPrice.currency || null);
			await bookingStore.hydrateServiceDetails();
			bookingStore.setNumberOfGuests(service.min_guests || 1);

			router.push({
				name: "BookingWizard",
				params: {
					serviceType: service.name || service.appointment_type || serviceType.value,
				},
			});
		} catch (error) {
			bookingError.value = error?.message || "Unable to add this package to booking.";
		} finally {
			isAddingToBooking.value = false;
		}
	}

	watch(
		serviceType,
		async (nextServiceType) => {
			if (!nextServiceType) {
				serviceDetailsStore.clearServiceDetails();
				return;
			}

			await serviceDetailsStore.fetchServiceDetails(nextServiceType);
		},
		{ immediate: true }
	);

	onBeforeUnmount(() => {
		serviceDetailsStore.clearServiceDetails();
	});

	return {
		serviceDetails,
		loading,
		error,
		packages,
		selectedPackage,
		formattedBenefits,
		formattedTechniques,
		longDescription,
		isAddingToBooking,
		bookingError,
		refreshServiceDetails,
		selectPackage,
		handleAddToBooking,
	};
}
