import { defineStore } from "pinia";

/**
 * Booking Cart Item
 * Represents a service package added to the booking cart
 */
export interface CartItem {
	id: string; // unique identifier for cart slot
	service_type: string; // Service Type name
	service_name: string; // Display name
	package_name: string; // Price name
	duration_minutes: number;
	price: number;
	currency: string;
	quantity: number;
	image?: string;
	metadata?: Record<string, any>;
}

/**
 * Booking Cart Store
 * Manages shopping cart for appointment bookings
 * Persists to localStorage
 */
export const useBookingCartStore = defineStore("booking-cart", {
	state: () => ({
		items: [] as CartItem[],
		lastUpdated: 0,
	}),

	getters: {
		/**
		 * Get all cart items
		 */
		cartItems(state): CartItem[] {
			return state.items;
		},

		/**
		 * Total number of items in cart (count ignores quantity)
		 */
		cartCount(state): number {
			return state.items.length;
		},

		/**
		 * Total quantity of all items
		 */
		totalQuantity(state): number {
			return state.items.reduce((sum, item) => sum + item.quantity, 0);
		},

		/**
		 * Subtotal of all items (price * quantity)
		 */
		cartSubtotal(state): number {
			return state.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
		},

		/**
		 * Check if cart is empty
		 */
		isEmpty(state): boolean {
			return state.items.length === 0;
		},

		/**
		 * Group items by service type for display
		 */
		groupedByService(state): Map<string, CartItem[]> {
			const grouped = new Map<string, CartItem[]>();
			for (const item of state.items) {
				if (!grouped.has(item.service_type)) {
					grouped.set(item.service_type, []);
				}
				grouped.get(item.service_type)!.push(item);
			}
			return grouped;
		},

		/**
		 * Get unique currency from all items (assumes all same currency)
		 */
		currency(state): string {
			return state.items.length > 0 ? state.items[0].currency : "USD";
		},
	},

	actions: {
		/**
		 * Generate unique ID for cart item
		 */
		_generateItemId(serviceType: string, packageName: string): string {
			return `${serviceType}::${packageName}`;
		},

		/**
		 * Check if item already exists in cart
		 */
		itemExists(serviceType: string, packageName: string): boolean {
			const id = this._generateItemId(serviceType, packageName);
			return this.items.some((item) => item.id === id);
		},

		/**
		 * Find item in cart
		 */
		_findItem(serviceType: string, packageName: string): CartItem | undefined {
			const id = this._generateItemId(serviceType, packageName);
			return this.items.find((item) => item.id === id);
		},

		/**
		 * Add service/package to cart
		 * If already exists, increments quantity
		 */
		addToCart(payload: {
			service_type: string;
			service_name: string;
			package_name: string;
			duration_minutes: number;
			price: number;
			currency: string;
			image?: string;
			metadata?: Record<string, any>;
		}): CartItem {
			const existing = this._findItem(payload.service_type, payload.package_name);

			if (existing) {
				// Item already exists, increment quantity
				existing.quantity += 1;
				this._updateTimestamp();
				this._persist();
				return existing;
			}

			// Create new cart item
			const newItem: CartItem = {
				id: this._generateItemId(payload.service_type, payload.package_name),
				service_type: payload.service_type,
				service_name: payload.service_name,
				package_name: payload.package_name,
				duration_minutes: payload.duration_minutes,
				price: payload.price,
				currency: payload.currency,
				quantity: 1,
				image: payload.image,
				metadata: payload.metadata,
			};

			this.items.push(newItem);
			this._updateTimestamp();
			this._persist();
			return newItem;
		},

		/**
		 * Remove item from cart
		 */
		removeFromCart(serviceType: string, packageName: string): boolean {
			const id = this._generateItemId(serviceType, packageName);
			const index = this.items.findIndex((item) => item.id === id);

			if (index === -1) {
				return false;
			}

			this.items.splice(index, 1);
			this._updateTimestamp();
			this._persist();
			return true;
		},

		/**
		 * Update quantity of an item
		 */
		updateQuantity(serviceType: string, packageName: string, quantity: number): boolean {
			const item = this._findItem(serviceType, packageName);

			if (!item) {
				return false;
			}

			if (quantity <= 0) {
				return this.removeFromCart(serviceType, packageName);
			}

			item.quantity = quantity;
			this._updateTimestamp();
			this._persist();
			return true;
		},

		/**
		 * Increment quantity of an item
		 */
		incrementQuantity(serviceType: string, packageName: string): boolean {
			const item = this._findItem(serviceType, packageName);
			if (!item) {
				return false;
			}

			item.quantity += 1;
			this._updateTimestamp();
			this._persist();
			return true;
		},

		/**
		 * Decrement quantity of an item (removes if reaches 0)
		 */
		decrementQuantity(serviceType: string, packageName: string): boolean {
			const item = this._findItem(serviceType, packageName);
			if (!item) {
				return false;
			}

			if (item.quantity <= 1) {
				return this.removeFromCart(serviceType, packageName);
			}

			item.quantity -= 1;
			this._updateTimestamp();
			this._persist();
			return true;
		},

		/**
		 * Clear all items from cart
		 */
		clearCart(): void {
			this.items = [];
			this._updateTimestamp();
			this._persist();
		},

		/**
		 * Load cart from localStorage
		 */
		hydrateCart(): void {
			try {
				const stored = localStorage.getItem("booking-cart");
				if (stored) {
					const data = JSON.parse(stored);
					this.items = data.items || [];
					this.lastUpdated = data.lastUpdated || 0;
				}
			} catch (error) {
				console.error("[BookingCart] Failed to hydrate from localStorage:", error);
				// Silently fail, keep default state
			}
		},

		/**
		 * Save cart to localStorage
		 */
		_persist(): void {
			try {
				const data = {
					items: this.items,
					lastUpdated: this.lastUpdated,
				};
				localStorage.setItem("booking-cart", JSON.stringify(data));
			} catch (error) {
				console.error("[BookingCart] Failed to persist to localStorage:", error);
				// Silently fail, cart remains in memory
			}
		},

		/**
		 * Update lastUpdated timestamp
		 */
		_updateTimestamp(): void {
			this.lastUpdated = Date.now();
		},

		/**
		 * Export cart data for booking workflow
		 */
		exportForBooking(): Array<{
			service_type: string;
			package_name: string;
			quantity: number;
			metadata?: Record<string, any>;
		}> {
			return this.items.map((item) => ({
				service_type: item.service_type,
				package_name: item.package_name,
				quantity: item.quantity,
				metadata: item.metadata,
			}));
		},
	},
});
