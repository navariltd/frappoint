<template>
	<div class="h-screen flex flex-col bg-surface-bright">
		<header class="border-b border-outline-variant/20 px-6 py-4 bg-surface">
			<div class="flex items-center gap-2 text-on-surface-variant mb-1">
				<span class="text-label-sm uppercase tracking-wider font-semibold text-primary"
					>Booking Workflow</span
				>
				<span class="material-symbols-outlined text-sm">chevron_right</span>
				<span class="text-label-sm">Step 2 of 3</span>
			</div>
			<h1 class="text-headline-lg font-headline-lg text-on-surface mb-1">
				Assign Guests and Schedule
			</h1>
			<p class="text-body-md text-on-surface-variant">
				Assign each selected service to a guest, then choose appointment date and slot.
			</p>
		</header>

		<div v-if="pageLoading" class="flex-1 flex items-center justify-center">
			<div class="space-y-4 text-center">
				<div
					class="inline-block w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
				></div>
				<p class="text-body-md text-on-surface-variant">Preparing booking workflow...</p>
			</div>
		</div>

		<div v-else-if="pageError" class="flex-1 flex items-center justify-center">
			<div class="space-y-4 text-center">
				<div class="inline-block p-4 rounded-full bg-error-container/30">
					<span class="material-symbols-outlined text-error text-[40px]"
						>error_outline</span
					>
				</div>
				<p class="text-body-md text-on-surface">{{ pageError }}</p>
				<button
					class="px-6 py-2 rounded-full bg-primary text-on-primary font-semibold hover:opacity-90"
					@click="initializePage"
				>
					Retry
				</button>
			</div>
		</div>

		<div v-else class="flex-1 flex overflow-hidden">
			<BookingServiceProgress
				:groups="serviceGroups"
				:active-assignment-id="activeAssignment?.id"
				@select="setActiveAssignment"
			/>

			<main class="flex-1 overflow-y-auto">
				<div v-if="activeAssignment" class="p-8 max-w-3xl mx-auto">
					<GuestAssignmentCard
						:assignment="activeAssignment"
						:current-index="activeAssignmentIndex"
						:total="totalGuests"
						:error="getAssignmentError(activeAssignment.id)"
						:is-loading-dates="isLoadingDates(activeAssignment.id)"
						:is-loading-slots="isLoadingSlots(activeAssignment.id)"
						@assign-guest="onAssignGuest"
						@select-date="onSelectDate"
						@select-slot="onSelectSlot"
					/>
				</div>
			</main>

			<aside
				class="w-80 border-l border-outline-variant/20 bg-surface-container-lowest p-6 flex flex-col overflow-y-auto"
			>
				<h3 class="text-headline-sm font-headline-sm text-on-surface mb-6">
					Booking Summary
				</h3>

				<div class="flex-1 space-y-6">
					<BookingAssignmentProgress
						:total="totalGuests"
						:completed="completedAssignments"
						:percent="progressPercentage"
					/>

					<div class="space-y-3">
						<p class="text-label-md font-semibold text-on-surface-variant">Services</p>
						<div
							v-for="group in serviceGroups"
							:key="group.serviceKey"
							class="p-3 rounded-lg bg-surface-container space-y-1"
						>
							<div class="flex justify-between items-start">
								<div>
									<p class="text-label-md font-semibold text-on-surface">
										{{ group.serviceName }}
									</p>
									<p class="text-label-sm text-on-surface-variant">
										{{ group.packageName }}
									</p>
								</div>
								<span class="text-label-md font-semibold"
									>{{ group.assignments.length }}x</span
								>
							</div>
							<div class="flex justify-between text-label-sm">
								<span class="text-on-surface-variant"
									>{{ group.duration }} minutes each</span
								>
								<span class="font-semibold"
									>{{ group.currency }}
									{{ (group.price * group.assignments.length).toFixed(2) }}</span
								>
							</div>
						</div>
					</div>

					<div class="pt-4 border-t border-outline-variant/20 space-y-3">
						<div class="flex justify-between text-body-sm">
							<span class="text-on-surface-variant">Subtotal</span>
							<span class="text-on-surface"
								>{{ draftBooking?.currency || "KES" }}
								{{ subtotal.toFixed(2) }}</span
							>
						</div>
						<div class="flex justify-between text-headline-sm font-semibold">
							<span class="text-on-surface">Total</span>
							<span class="text-primary"
								>{{ draftBooking?.currency || "KES" }}
								{{ subtotal.toFixed(2) }}</span
							>
						</div>
					</div>
				</div>

				<AssignmentConfirmationPanel
					:can-confirm="canConfirmCurrent"
					:saving="activeAssignment ? isSavingAssignment(activeAssignment.id) : false"
					:workflow-complete="isWorkflowComplete"
					:disable-previous="activeAssignmentIndex === 0"
					@confirm="confirmCurrentAssignment"
					@previous="goPrevious"
					@proceed="proceedToPayment"
				/>
			</aside>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useBookingWorkflow } from "@/composables/useBookingWorkflow";
import BookingServiceProgress from "@/components/booking/BookingServiceProgress.vue";
import GuestAssignmentCard from "@/components/booking/GuestAssignmentCard.vue";
import BookingAssignmentProgress from "@/components/booking/BookingAssignmentProgress.vue";
import AssignmentConfirmationPanel from "@/components/booking/AssignmentConfirmationPanel.vue";

const router = useRouter();
const pageLoading = ref(true);
const pageError = ref("");

const {
	draftBooking,
	assignments,
	activeAssignment,
	activeAssignmentIndex,
	totalGuests,
	completedAssignments,
	progressPercentage,
	isWorkflowComplete,
	startWorkflow,
	setActiveAssignment,
	assignGuest,
	loadDates,
	chooseDate,
	loadSlots,
	chooseSlot,
	confirmAssignment,
	getAssignmentError,
	isLoadingDates,
	isLoadingSlots,
	isSavingAssignment,
} = useBookingWorkflow();

const serviceGroups = computed(() => {
	const groups: Array<{
		serviceKey: string;
		serviceName: string;
		packageName: string;
		duration: number;
		price: number;
		currency: string;
		assignments: Array<any>;
	}> = [];
	const grouped = new Map<string, typeof groups[number]>();

	assignments.value.forEach((assignment, index) => {
		if (!grouped.has(assignment.service_key)) {
			grouped.set(assignment.service_key, {
				serviceKey: assignment.service_key,
				serviceName: assignment.service_name,
				packageName: assignment.package_name,
				duration: assignment.duration_minutes,
				price: assignment.price,
				currency: assignment.currency,
				assignments: [],
			});
		}
		grouped.get(assignment.service_key)!.assignments.push({
			...assignment,
			globalIndex: index,
		});
	});

	for (const value of grouped.values()) groups.push(value);
	return groups;
});

const subtotal = computed(() =>
	assignments.value.reduce((sum, assignment) => sum + Number(assignment.price || 0), 0)
);

const canConfirmCurrent = computed(() => {
	if (!activeAssignment.value) return false;
	return Boolean(
		activeAssignment.value.guest_full_name &&
			activeAssignment.value.selected_date &&
			activeAssignment.value.selected_slot_id
	);
});

async function initializePage() {
	pageLoading.value = true;
	pageError.value = "";
	try {
		await startWorkflow();
		if (activeAssignment.value) {
			if (
				!Array.isArray(activeAssignment.value.available_dates) ||
				!activeAssignment.value.available_dates.length
			) {
				await loadDates(activeAssignment.value.id);
			}
			if (
				activeAssignment.value.selected_date &&
				(!Array.isArray(activeAssignment.value.available_slots) ||
					!activeAssignment.value.available_slots.length)
			) {
				await loadSlots(activeAssignment.value.id);
			}
		}
	} catch (error: any) {
		pageError.value = error?.message || "Unable to initialize booking workflow.";
	} finally {
		pageLoading.value = false;
	}
}

function onAssignGuest(payload: { fullName: string; email?: string; mobile?: string }) {
	if (!activeAssignment.value) return;
	assignGuest(activeAssignment.value.id, payload);
}

async function onSelectDate(date: string) {
	if (!activeAssignment.value) return;
	try {
		await chooseDate(activeAssignment.value.id, date);
	} catch (error: any) {
		console.error("[BookingWorkflow] Date selection failed:", error);
	}
}

async function onSelectSlot(slotId: string) {
	if (!activeAssignment.value) return;
	try {
		// Step 1: Update selected slot in store
		chooseSlot(activeAssignment.value.id, slotId);
		console.log(
			`[BookingWorkflow] Slot selected for assignment ${activeAssignment.value.id}: ${slotId}`
		);

		// Step 2: Auto-trigger appointment creation if all required fields are present
		const assignmentId = activeAssignment.value.id;
		const assignment = activeAssignment.value;

		if (
			assignment.guest_full_name &&
			assignment.selected_date &&
			assignment.selected_slot_id
		) {
			console.log(
				`[BookingWorkflow] All fields present for ${assignmentId}. Auto-triggering appointment creation...`
			);
			await confirmCurrentAssignment();
		}
	} catch (error: any) {
		console.error("[BookingWorkflow] Slot selection failed:", error);
		// Error is managed by store, just log for debugging
	}
}

async function confirmCurrentAssignment() {
	if (!activeAssignment.value) return;
	const currentAssignmentId = activeAssignment.value.id;

	try {
		console.log(`[BookingWorkflow] Starting appointment creation for ${currentAssignmentId}`);
		await confirmAssignment(currentAssignmentId);
		console.log(
			`[BookingWorkflow] Appointment created successfully. Active index is now: ${activeAssignmentIndex.value}`
		);

		// After appointment creation, activeAssignmentIndex has changed to next guest
		// Load dates for the new active guest if not already loaded
		if (
			activeAssignment.value &&
			(!Array.isArray(activeAssignment.value.available_dates) ||
				!activeAssignment.value.available_dates.length)
		) {
			console.log(
				`[BookingWorkflow] Loading dates for next guest: ${activeAssignment.value.id}`
			);
			await loadDates(activeAssignment.value.id);
		}
	} catch (error: any) {
		console.error(
			`[BookingWorkflow] Appointment creation failed for ${currentAssignmentId}:`,
			error
		);
		// Error message is managed by store assignmentErrors
	}
}

function goPrevious() {
	if (activeAssignmentIndex.value > 0) {
		setActiveAssignment(activeAssignmentIndex.value - 1);
	}
}

async function proceedToPayment() {
	if (!isWorkflowComplete.value || !draftBooking.value?.id) {
		pageError.value = "Complete all assignments before continuing to payment.";
		return;
	}

	await router.push({
		name: "Checkout",
		params: { bookingId: draftBooking.value.id },
	});
}

onMounted(() => {
	initializePage();
});

// Watch for active assignment changes (e.g., user clicks Previous button)
// Ensure dates are loaded for the current guest
watch(
	() => activeAssignment.value?.id,
	async (newAssignmentId) => {
		if (!newAssignmentId) return;

		console.log(`[BookingWorkflow] Active assignment changed to: ${newAssignmentId}`);

		const assignment = activeAssignment.value;
		if (
			assignment &&
			(!Array.isArray(assignment.available_dates) || !assignment.available_dates.length)
		) {
			console.log(`[BookingWorkflow] Loading dates for assignment: ${newAssignmentId}`);
			try {
				await loadDates(newAssignmentId);
			} catch (error) {
				console.error(
					`[BookingWorkflow] Failed to load dates for assignment ${newAssignmentId}:`,
					error
				);
			}
		}
	}
);
</script>
