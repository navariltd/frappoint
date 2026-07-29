import { computed, onBeforeUnmount, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { useServiceDetailsStore } from "@/stores/serviceDetails.store";
import { useBookingCart } from "@/composables/useBookingCart";

export function useServiceDetails() {
	const route = useRoute();
	const serviceDetailsStore = useServiceDetailsStore();
	const { addItem } = useBookingCart();
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
	const bookingSuccess = ref("");

	async function refreshServiceDetails() {
		if (!serviceType.value) {
			serviceDetailsStore.clearServiceDetails();
			return null;
		}

		return serviceDetailsStore.fetchServiceDetails(serviceType.value);
	}

	function selectPackage(packageItem) {
		serviceDetailsStore.setSelectedPackage(packageItem);
		bookingError.value = "";
		bookingSuccess.value = "";
	}

	async function handleAddToBooking() {
		const service = serviceDetails.value;
		const selectedPrice = selectedPackage.value;

		bookingError.value = "";
		bookingSuccess.value = "";

		if (!service || !selectedPrice || isAddingToBooking.value) {
			return;
		}

		isAddingToBooking.value = true;

		try {
			const serviceId =
				service.name || service.appointment_type || serviceType.value;
			const packageName = selectedPrice.price_name || selectedPrice.name;
			const duration = Number(
				selectedPrice.duration || service.default_duration_in_minutes
			);
			const price = Number(selectedPrice.amount);
			const currency = selectedPrice.currency;

			if (
				!serviceId ||
				!packageName ||
				!Number.isFinite(duration) ||
				duration <= 0 ||
				!Number.isFinite(price) ||
				!currency
			) {
				throw new Error("This service package is not available for booking.");
			}

			const cartItem = addItem({
				service_type: service.name || service.appointment_type || serviceType.value,
				service_name: service.appointment_type,
				package_name: packageName,
				duration_minutes: duration,
				price,
				currency,
				image: service.image,
				metadata: {
					item_group: service.item_group,
					item_name: service.item_name,
					min_guests: service.min_guests,
					max_guests: service.max_guests,
					pricing_model: selectedPrice.pricing_model,
					guest_count: selectedPrice.guest_count,
				},
			});

			bookingSuccess.value =
				cartItem.quantity > 1
					? `Quantity updated to ${cartItem.quantity} in your booking cart.`
					: "Added to your booking cart.";
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
		bookingSuccess,
		refreshServiceDetails,
		selectPackage,
		handleAddToBooking,
	};
}
