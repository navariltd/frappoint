import { computed, onBeforeUnmount, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useBookingStore } from "@/stores/bookingStore";
import { useServiceDetailsStore } from "@/stores/serviceDetails.store";
import { useBookingCart } from "@/composables/useBookingCart";

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
		const { addItem } = useBookingCart();

		bookingError.value = "";

		if (!service || !selectedPrice || isAddingToBooking.value) {
			return;
		}

		isAddingToBooking.value = true;

		try {
			// Add to booking cart
			addItem({
				service_type: service.name || service.appointment_type || serviceType.value,
				service_name: service.appointment_type,
				package_name: selectedPrice.price_name || selectedPrice.name,
				duration_minutes: selectedPrice.duration || service.default_duration_in_minutes || 30,
				price: selectedPrice.amount || 0,
				currency: selectedPrice.currency || "USD",
				image: service.image,
				metadata: {
					min_guests: service.min_guests,
					max_guests: service.max_guests,
				},
			});

			// Success - item added to cart
			bookingError.value = "";
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
