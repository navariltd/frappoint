<template>
	<aside
		class="w-96 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-screen max-h-screen overflow-hidden"
	>
		<div class="p-6 border-b border-slate-100 dark:border-slate-800 shrink-0">
			<h3
				class="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2"
			>
				<span class="material-symbols-outlined text-primary text-[20px]"
					>person_search</span
				>
				Customer
			</h3>

			<div v-if="!store.customer.fullName" class="relative">
				<div class="relative group">
					<span
						class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors"
					>
						search
					</span>
					<input
						v-model="searchQuery"
						@focus="isDropdownVisible = true"
						@blur="setTimeout(() => (isDropdownVisible = false), 200)"
						class="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-800 border-2 border-transparent rounded-xl text-sm focus:bg-white focus:ring-4 focus:ring-primary/10 focus:border-primary/20 outline-none transition-all"
						placeholder="Search by name or phone..."
						type="text"
					/>
				</div>

				<div
					v-if="isDropdownVisible"
					class="absolute z-50 w-full mt-2 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
				>
					<div
						v-if="!searchQuery"
						class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-50 dark:bg-slate-800/50"
					>
						Recent Customers
					</div>

					<div class="max-h-64 overflow-y-auto">
						<div
							v-if="customers.loading"
							class="p-4 text-center text-xs text-slate-500"
						>
							Searching...
						</div>

						<button
							v-for="customer in customers.data"
							:key="customer.name"
							@click="handleSelectCustomer(customer)"
							class="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors border-b border-slate-50 dark:border-slate-800 last:border-0"
						>
							<div
								class="size-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-[10px] font-bold"
							>
								{{ getInitials(customer.customer_name) }}
							</div>
							<div class="text-left">
								<p class="text-sm font-semibold text-slate-900 dark:text-white">
									{{ customer.customer_name }}
								</p>
								<p class="text-[10px] text-slate-500">
									{{ customer.mobile_no || "No phone" }}
								</p>
							</div>
						</button>

						<div
							v-if="!customers.loading && customers.data?.length === 0"
							class="p-4 text-center text-xs text-slate-400"
						>
							No customers found.
						</div>
					</div>
				</div>
			</div>

			<div
				v-else
				class="flex items-center justify-between gap-3 p-3 bg-primary/5 border border-primary/20 rounded-xl"
			>
				<div class="flex items-center gap-3 min-w-0">
					<div
						class="size-10 rounded-full bg-primary text-white flex items-center justify-center font-bold text-xs shrink-0"
					>
						{{ getInitials(store.customer.fullName) }}
					</div>
					<div class="flex flex-col min-w-0">
						<h4 class="font-bold text-slate-900 dark:text-white text-sm truncate">
							{{ store.customer.fullName }}
						</h4>
						<p class="text-[11px] text-slate-500 font-medium truncate">
							{{ store.customer.mobileNo }}
						</p>
					</div>
				</div>
				<button
					@click="store.setCustomer({ fullName: '', mobileNo: '', email: '' })"
					class="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 transition-all"
				>
					<span class="material-symbols-outlined text-[20px]">close</span>
				</button>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto p-6 scrollbar-hide">
			<h3
				class="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2 sticky top-0 bg-white dark:bg-slate-900 z-10 pb-2"
			>
				<span class="material-symbols-outlined text-primary">receipt_long</span>
				Booking Summary ({{ store.guests.length }})
			</h3>

			<div class="space-y-6">
				<div
					v-for="(guest, index) in store.guests"
					:key="index"
					class="flex justify-between items-start text-sm animate-in fade-in slide-in-from-right-2"
				>
					<div class="flex-1 pr-4">
						<p class="text-slate-700 dark:text-slate-300 font-bold">
							{{ guest.appointment_type || "Select Service..." }}
							<span v-if="guest.duration" class="text-slate-400 font-normal"
								>({{ guest.duration }}m)</span
							>
						</p>
						<p class="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
							<span class="material-symbols-outlined text-[14px]">person</span>
							For {{ guest.guest_full_name || "Unnamed Guest" }}
						</p>
						<p
							v-if="guest.slot"
							class="text-[10px] text-primary font-bold uppercase tracking-wider mt-1.5 flex items-center gap-1"
						>
							<span class="material-symbols-outlined text-[14px]"
								>event_available</span
							>
							{{ guest.date }} @
							{{
								typeof guest.slot === "object" ? guest.slot.start_time : guest.slot
							}}
						</p>
					</div>
					<span class="font-bold text-slate-900 dark:text-white">
						{{ formatCurrency(guest.amount) }}
					</span>
				</div>

				<div v-if="store.guests.length === 0" class="text-center py-20 opacity-40">
					<span class="material-symbols-outlined text-4xl mb-2">shopping_basket</span>
					<p class="text-xs font-medium">No services added yet</p>
				</div>
			</div>
		</div>

		<div
			class="mt-auto p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 shrink-0"
		>
			<div class="space-y-3">
				<div class="flex justify-between text-sm">
					<span class="text-slate-500 font-medium">Subtotal</span>
					<span class="text-slate-900 dark:text-white font-semibold">{{
						formatCurrency(store.totalAmount)
					}}</span>
				</div>
				<div class="flex justify-between text-sm">
					<span class="text-slate-500 font-medium">Tax (Included)</span>
					<span class="text-slate-900 dark:text-white font-semibold">{{
						formatCurrency(0)
					}}</span>
				</div>

				<div
					class="pt-3 mt-1 border-t-2 border-dashed border-slate-200 dark:border-slate-700"
				>
					<div class="flex justify-between items-center">
						<span
							class="text-slate-900 dark:text-white font-black text-base uppercase tracking-tight"
							>Total</span
						>
						<span class="text-2xl font-black text-primary">{{
							formatCurrency(store.totalAmount)
						}}</span>
					</div>
				</div>

				<button
					@click="handleCheckout"
					:disabled="!store.isComplete || store.loading"
					class="w-full bg-slate-900 bg-primary hover:scale-[1.02] active:scale-95 disabled:bg-slate-200 disabled:scale-100 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl mt-4 transition-all shadow-xl shadow-slate-200 dark:shadow-none flex items-center justify-center gap-2"
				>
					<span v-if="store.loading" class="animate-spin material-symbols-outlined"
						>sync</span
					>
					<span v-else class="material-symbols-outlined">payments</span>
					{{ store.loading ? "Processing..." : "Complete Booking" }}
				</button>
			</div>
		</div>
	</aside>
</template>

<script setup>
import { ref, computed } from "vue";
import { createListResource } from "frappe-ui";
import { useBookingStore } from "@/stores/bookingStore";

const store = useBookingStore();
const searchQuery = ref("");
const isDropdownVisible = ref(false);

const customers = createListResource({
	doctype: "Customer",
	fields: ["name", "customer_name", "mobile_no", "email_id"],
	filters: computed(() => {
		// If query is present, filter by name. Otherwise, just fetch the first 10.
		return searchQuery.value ? { customer_name: ["like", `%${searchQuery.value}%`] } : {};
	}),
	pageLength: 10,
	auto: true,
});

function handleSelectCustomer(customer) {
	store.setCustomer({
		customer: customer.name,
		fullName: customer.customer_name,
		mobileNo: customer.mobile_no,
		email: customer.email_id,
	});

	if (store.guests.length > 0 && !store.guests[0].full_name) {
		store.updateGuest(0, { full_name: customer.customer_name });
	}
	searchQuery.value = "";
	isDropdownVisible.value = false;
}

function formatCurrency(amount) {
	return new Intl.NumberFormat("en-KE", {
		style: "currency",
		currency: "KES",
	}).format(amount || 0);
}

function getInitials(name) {
	if (!name) return "??";
	return name
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.substring(0, 2);
}

async function handleCheckout() {
	try {
		await store.submitBooking();
	} catch (e) {
		console.error("Submission error:", e);
	}
}
</script>
