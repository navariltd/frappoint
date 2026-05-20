import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useBookingCartStore } from "@/stores/bookingCart.store";

/**
 * Composable for interacting with the booking cart
 * Provides simplified API and derived state
 */
export function useBookingCart() {
	const cartStore = useBookingCartStore();
	const { cartItems, cartCount, totalQuantity, cartSubtotal, isEmpty, currency, groupedByService } =
		storeToRefs(cartStore);

	/**
	 * Add service package to cart
	 */
	function addItem(payload: {
		service_type: string;
		service_name: string;
		package_name: string;
		duration_minutes: number;
		price: number;
		currency?: string;
		image?: string;
		metadata?: Record<string, any>;
	}) {
		return cartStore.addToCart({
			currency: "USD",
			...payload,
		});
	}

	/**
	 * Remove item from cart
	 */
	function removeItem(serviceType: string, packageName: string) {
		return cartStore.removeFromCart(serviceType, packageName);
	}

	/**
	 * Update quantity
	 */
	function setQuantity(serviceType: string, packageName: string, quantity: number) {
		return cartStore.updateQuantity(serviceType, packageName, quantity);
	}

	/**
	 * Increment quantity
	 */
	function addOne(serviceType: string, packageName: string) {
		return cartStore.incrementQuantity(serviceType, packageName);
	}

	/**
	 * Decrement quantity
	 */
	function removeOne(serviceType: string, packageName: string) {
		return cartStore.decrementQuantity(serviceType, packageName);
	}

	/**
	 * Clear entire cart
	 */
	function clear() {
		cartStore.clearCart();
	}

	/**
	 * Check if item exists
	 */
	function hasItem(serviceType: string, packageName: string) {
		return cartStore.itemExists(serviceType, packageName);
	}

	/**
	 * Get item quantity
	 */
	function getItemQuantity(serviceType: string, packageName: string): number {
		const item = cartItems.value.find(
			(i) => i.service_type === serviceType && i.package_name === packageName
		);
		return item?.quantity || 0;
	}

	/**
	 * Get all items for a specific service
	 */
	function getServiceItems(serviceType: string) {
		return cartItems.value.filter((item) => item.service_type === serviceType);
	}

	/**
	 * Hydrate cart from storage
	 */
	function hydrate() {
		cartStore.hydrateCart();
	}

	/**
	 * Export cart for booking workflow
	 */
	function exportData() {
		return cartStore.exportForBooking();
	}

	return {
		// State
		cartItems,
		cartCount,
		totalQuantity,
		cartSubtotal,
		isEmpty,
		currency,
		groupedByService,

		// Actions
		addItem,
		removeItem,
		setQuantity,
		addOne,
		removeOne,
		clear,
		hasItem,
		getItemQuantity,
		getServiceItems,
		hydrate,
		exportData,
	};
}
