<template>
	<!-- Drawer Overlay -->
	<div
		v-if="open"
		class="fixed inset-0 z-40 bg-black/30 transition-opacity duration-300"
		@click="$emit('close')"
		:class="{ 'opacity-0': !open, 'opacity-100': open }"
	></div>

	<!-- Drawer Panel -->
	<div
		class="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-surface bg-white flex flex-col transition-transform duration-300 shadow-lg"
		:class="{ 'translate-x-0': open, 'translate-x-full': !open }"
	>
		<!-- Header -->
		<div
			class="flex-shrink-0 border-b border-outline-variant/20 px-6 py-4 flex items-center justify-between"
		>
			<h2 class="text-headline-md font-headline-md text-on-surface">Your Cart</h2>
			<button
				class="p-2 rounded-full hover:bg-outline-variant/10 transition-colors"
				@click="$emit('close')"
				aria-label="Close cart"
			>
				<span class="material-symbols-outlined">close</span>
			</button>
		</div>

		<!-- Content -->
		<div v-if="!isEmpty" class="flex-1 overflow-y-auto px-6">
			<div class="space-y-2">
				<BookingCartItem
					v-for="item in cartItems"
					:key="`${item.service_type}-${item.package_name}`"
					:item="item"
					:currency="currency"
					@increment="addOne(item.service_type, item.package_name)"
					@decrement="removeOne(item.service_type, item.package_name)"
					@remove="removeItem(item.service_type, item.package_name)"
				/>
			</div>
		</div>

		<!-- Empty State -->
		<div v-else class="flex-1 flex items-center justify-center">
			<EmptyBookingCart @browse="$emit('browse')" />
		</div>

		<!-- Footer -->
		<div
			v-if="!isEmpty"
			class="flex-shrink-0 border-t border-outline-variant/20 px-6 py-6 space-y-4 bg-surface-container-low"
		>
			<!-- Summary -->
			<BookingCartSummary />

			<div
				v-if="continueError"
				role="alert"
				class="flex items-start gap-2 rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-body-sm text-error"
			>
				<span class="material-symbols-outlined text-[20px]">error</span>
				<span>{{ continueError }}</span>
			</div>

			<!-- Actions -->
			<div class="space-y-3">
				<button
					class="w-full px-6 py-3 rounded-full bg-primary text-on-primary font-semibold text-body-md hover:bg-primary/90 transition-colors"
					@click="handleContinueBooking"
					:disabled="isProcessing"
				>
					<span v-if="!isProcessing">Continue Booking</span>
					<span v-else class="flex items-center justify-center gap-2">
						<span
							class="inline-block w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin"
						></span>
						Processing...
					</span>
				</button>

				<button
					class="w-full px-6 py-2.5 rounded-full border border-outline-variant text-on-surface font-semibold text-body-md hover:bg-outline-variant/10 transition-colors"
					@click="$emit('close')"
				>
					Continue Shopping
				</button>

				<button
					class="w-full px-6 py-2.5 rounded-full text-error font-semibold text-body-md hover:bg-error/10 transition-colors"
					@click="handleClearCart"
				>
					Clear Cart
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useBookingCart } from "@/composables/useBookingCart";
import { useAuthStore } from "@/stores/auth";
import { useBookingWorkflow } from "@/composables/useBookingWorkflow";
import BookingCartItem from "./BookingCartItem.vue";
import BookingCartSummary from "./BookingCartSummary.vue";
import EmptyBookingCart from "./EmptyBookingCart.vue";

defineProps<{
	open: boolean;
}>();

const emit = defineEmits<{
	close: [];
	browse: [];
}>();

const router = useRouter();
const { cartItems, isEmpty, currency, addOne, removeOne, removeItem, clear } = useBookingCart();
const auth = useAuthStore();
const workflow = useBookingWorkflow();

const isProcessing = ref(false);
const continueError = ref("");

async function handleContinueBooking() {
	if (isProcessing.value) return;

	isProcessing.value = true;
	continueError.value = "";
	try {
		await auth.refreshUser();

		if (!auth.isLoggedIn) {
			await router.push({
				name: "Login",
				query: { redirect: "/booking/workflow" },
			});
			emit("close");
			return;
		}

		await workflow.startWorkflow();
		await router.push({
			name: "BookingWorkflow",
		});
		emit("close");
	} catch (error: any) {
		console.error("[BookingCartDrawer] Navigation failed:", error);
		continueError.value =
			error?.message || "We could not start your booking. Please try again.";
	} finally {
		isProcessing.value = false;
	}
}

function handleClearCart() {
	if (confirm("Are you sure you want to clear your cart? This action cannot be undone.")) {
		clear();
	}
}
</script>
