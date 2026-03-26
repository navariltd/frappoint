<template>
	<div class="max-w-4xl mx-auto">
		<!-- Header -->
		<div class="flex items-center justify-between mb-8">
			<div>
				<h1 class="text-2xl font-bold text-slate-900 dark:text-white">New Session</h1>
				<p class="text-slate-500 text-sm mt-1">
					Add guests and assign services for this booking.
				</p>
			</div>

			<button
				@click="showModal = true"
				class="flex items-center gap-2 bg-primary/80 hover:bg-primary/90 active:scale-95 text-slate-900 font-semibold px-4 py-2.5 rounded-lg transition-all shadow-sm"
			>
				<span class="material-symbols-outlined text-[20px]">person_add</span>
				<span>Add Guest</span>
			</button>
		</div>

		<!-- Guests List -->
		<div class="space-y-4">
			<h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
				Guests & Services ({{ guests.length }})
			</h3>

			<div v-if="guests.length > 0" class="grid gap-4">
				<GuestCard
					v-for="guest in guests"
					:key="guest.id"
					:guest="guest"
					@remove="removeGuest"
					@edit="editGuest"
				/>
			</div>

			<div
				v-else
				class="border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center bg-slate-50/30 dark:bg-slate-900/30"
			>
				<div
					class="size-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<span class="material-symbols-outlined text-slate-400 text-3xl"
						>group_add</span
					>
				</div>
				<p class="text-slate-600 dark:text-slate-400 font-medium">No guests added yet.</p>
				<p class="text-slate-400 text-xs mb-4">
					Start by adding your first guest to the session.
				</p>
				<button
					@click="showModal = true"
					class="inline-flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-4 py-2 rounded-lg text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition-colors shadow-sm"
				>
					Add First Guest
				</button>
			</div>
		</div>

		<!-- Add/Edit Guest Modal -->
		<Dialog
			v-model="showModal"
			:options="{
				title: modalTitle,
				size: '5xl',
			}"
		>
			<template #body-content>
				<NewGuestModal
					@close="closeModal"
					@save="handleGuestSaved"
					ref="newGuestModalRef"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, computed, nextTick } from "vue";
import { Dialog } from "frappe-ui";
import GuestCard from "@/components/bookings/GuestCard.vue";
import NewGuestModal from "@/components/bookings/NewGuestModal.vue";
import { useBookingStore } from "@/stores/bookingStore";

const showModal = ref(false);
const newGuestModalRef = ref(null);
const editingGuestIndex = ref(null);

const bookingStore = useBookingStore();
const guests = computed(() => bookingStore.guests);

// Modal title dynamic
const modalTitle = computed(() => (editingGuestIndex.value !== null ? "Edit Guest" : "Add Guest"));

// Open modal to edit existing guest
async function editGuest(guest) {
	const index = guests.value.findIndex((g) => g.id === guest.id);
	if (index === -1) return;

	editingGuestIndex.value = index;
	showModal.value = true; // 1. Open the dialog

	// 2. Wait for Vue to render the modal so the 'ref' is no longer null
	await nextTick();

	// 3. Now call the child function
	if (newGuestModalRef.value) {
		newGuestModalRef.value.editGuest(index);
	}
}

// Remove guest from store
function removeGuest(guestId) {
	bookingStore.removeGuest(guestId);
}

// Handle save from modal
function handleGuestSaved(guest) {
	if (editingGuestIndex.value !== null) {
		// Keep the existing ID when updating
		bookingStore.updateGuest(editingGuestIndex.value, { ...guest });
		editingGuestIndex.value = null;
	} else {
		// Create new ID only for new guests
		const guestWithId = { ...guest, id: Date.now() };
		bookingStore.addGuest(guestWithId);
	}
	showModal.value = false;
}

// Close modal (reset editing state)
function closeModal() {
	editingGuestIndex.value = null;
	showModal.value = false;
}
</script>
