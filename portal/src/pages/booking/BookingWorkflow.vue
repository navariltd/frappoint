<template>
	<main class="flex-grow bg-surface-bright">
		<div class="max-w-[1200px] mx-auto px-container-padding py-section-gap">
			<div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
				<div>
					<nav class="flex items-center gap-2 mb-2">
						<router-link
							:to="{ name: 'Bookings' }"
							class="text-label-sm text-outline uppercase tracking-wider hover:text-primary transition-colors"
						>
							My Bookings
						</router-link>
						<span class="material-symbols-outlined text-[14px] text-outline"
							>chevron_right</span
						>
						<span class="text-label-sm text-primary font-bold uppercase tracking-wider"
							>Assign Guests</span
						>
					</nav>
					<h1 class="font-headline-lg text-headline-lg text-on-surface mb-2">
						Assign Guests
					</h1>
					<p class="text-on-surface-variant font-body-md">
						Step 2 of 4 — Tell us who will be enjoying each service.
					</p>
				</div>
				<div class="flex items-center gap-4 font-label-md text-label-md">
					<span class="text-on-surface-variant">Selection</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-primary">Guests</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant font-bold">Review</span>
					<span class="material-symbols-outlined text-[16px] text-outline"
						>arrow_forward</span
					>
					<span class="text-on-surface-variant">Checkout</span>
				</div>
			</div>

			<div v-if="pageLoading" class="flex items-center justify-center py-20">
				<div class="space-y-4 text-center">
					<div
						class="inline-block w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
					></div>
					<p class="text-body-md text-on-surface-variant">
						Preparing booking workflow...
					</p>
				</div>
			</div>

			<div v-else-if="pageError" class="flex items-center justify-center py-20">
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

			<div v-else class="space-y-gutter">
				<section
					v-for="service in serviceGroups"
					:key="service.serviceKey"
					class="bg-white rounded-xl custom-shadow p-6 transition-all duration-300 border border-transparent hover:border-primary-container"
				>
					<div class="flex items-start justify-between gap-4 mb-6">
						<div class="flex items-center gap-4 min-w-0">
							<div
								class="w-16 h-16 rounded-lg bg-primary-container/20 text-primary flex items-center justify-center flex-shrink-0"
							>
								<span class="material-symbols-outlined text-[28px]">spa</span>
							</div>
							<div class="min-w-0">
								<h3 class="font-headline-sm text-headline-sm text-on-surface">
									{{ service.serviceName }}
								</h3>
								<p class="font-label-sm text-on-surface-variant">
									{{ service.duration }} Minutes • {{ service.packageName }}
								</p>
							</div>
						</div>
						<div class="flex items-center gap-3 shrink-0">
							<div class="text-right">
								<p class="font-label-md text-on-surface">
									{{ serviceCompleted(service) }}/{{
										service.assignments.length
									}}
								</p>
								<p class="font-label-sm text-on-surface-variant">
									guests assigned
								</p>
							</div>
							<button
								:disabled="!isServiceComplete(service)"
								class="w-10 h-10 rounded-full border border-outline-variant/40 flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:border-primary"
								@click="toggleService(service.serviceKey)"
							>
								<span class="material-symbols-outlined text-on-surface-variant">
									{{
										isServiceExpanded(service.serviceKey)
											? "expand_less"
											: "expand_more"
									}}
								</span>
							</button>
						</div>
					</div>

					<div v-if="isServiceExpanded(service.serviceKey)" class="space-y-4">
						<div
							v-for="assignment in service.assignments"
							:key="assignment.id"
							class="rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 transition-all"
						>
							<div
								class="flex items-center justify-between gap-3"
								:class="canCollapseGuest(assignment) ? 'cursor-pointer' : ''"
								@click="toggleGuestCard(assignment.id, assignment.globalIndex)"
							>
								<div>
									<label class="font-label-md text-on-surface"
										>Guest {{ assignment.guest_index + 1 }}</label
									>
									<p class="font-label-sm text-on-surface-variant">
										{{ guestSummary(assignment) }}
									</p>
								</div>
								<div class="flex items-center gap-2">
									<span
										class="px-3 py-1 rounded-full font-label-sm"
										:class="
											isAssignmentComplete(assignment)
												? 'bg-primary-container/30 text-primary'
												: 'bg-surface-container text-on-surface-variant'
										"
									>
										{{
											isAssignmentComplete(assignment)
												? "Assigned"
												: "Pending"
										}}
									</span>
									<span
										v-if="canCollapseGuest(assignment)"
										class="material-symbols-outlined text-on-surface-variant"
									>
										{{
											isGuestExpanded(assignment.id)
												? "expand_less"
												: "expand_more"
										}}
									</span>
								</div>
							</div>

							<div v-if="isGuestExpanded(assignment.id)" class="space-y-4 pt-4">
								<div
									v-if="getAssignmentError(assignment.id)"
									class="p-3 rounded-lg bg-error-container/30 border border-error-container"
								>
									<div class="flex gap-3">
										<span class="material-symbols-outlined text-error"
											>error</span
										>
										<p class="text-body-sm text-on-error-container">
											{{ getAssignmentError(assignment.id) }}
										</p>
									</div>
								</div>

								<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
									<div class="relative">
										<input
											:value="assignment.guest_full_name"
											type="text"
											placeholder="Full Name"
											class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
											@input="
												onAssignGuest(assignment.id, {
													fullName: ($event.target as HTMLInputElement)
														.value,
													email: assignment.guest_email,
													mobile: assignment.guest_mobile,
												})
											"
										/>
									</div>
									<div class="relative">
										<input
											:value="assignment.guest_email"
											type="email"
											placeholder="Email Address (Optional)"
											class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
											@input="
												onAssignGuest(assignment.id, {
													fullName: assignment.guest_full_name,
													email: ($event.target as HTMLInputElement)
														.value,
													mobile: assignment.guest_mobile,
												})
											"
										/>
									</div>
									<div class="relative">
										<input
											:value="assignment.guest_mobile"
											type="tel"
											placeholder="Phone Number (Optional)"
											class="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 font-body-md text-on-surface focus:ring-2 focus:ring-primary transition-all"
											@input="
												onAssignGuest(assignment.id, {
													fullName: assignment.guest_full_name,
													email: assignment.guest_email,
													mobile: ($event.target as HTMLInputElement)
														.value,
												})
											"
										/>
									</div>
								</div>

								<div class="flex items-center justify-between gap-4 flex-wrap">
									<div
										v-if="assignment.selected_date"
										class="flex items-center gap-2 text-on-surface-variant"
									>
										<span
											class="material-symbols-outlined text-[18px] text-primary"
											>event</span
										>
										<span class="font-label-sm">
											{{ assignment.selected_date }}
											<template v-if="assignment.selected_slot"
												>•
												{{
													formatTime(assignment.selected_slot.startTime)
												}}</template
											>
										</span>
									</div>
									<button
										class="text-primary font-label-sm hover:underline transition-all flex items-center gap-1 disabled:opacity-50 disabled:no-underline"
										:disabled="!assignment.guest_full_name"
										@click.stop="
											openDateTimeModal(
												assignment.id,
												assignment.globalIndex
											)
										"
									>
										<span class="material-symbols-outlined text-[16px]"
											>calendar_clock</span
										>
										{{
											assignment.selected_slot_id
												? "Change Time Slot"
												: "Pick Time Slot"
										}}
									</button>
								</div>
							</div>
						</div>
					</div>
				</section>
			</div>

			<div
				v-if="!pageLoading && !pageError"
				class="mt-section-gap flex flex-col items-center gap-stack-md"
			>
				<button
					:disabled="!isWorkflowComplete"
					class="w-full max-w-md bg-primary text-on-primary font-headline-sm py-4 rounded-full deep-shadow hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
					@click="proceedToPayment"
				>
					Proceed to Review
					<span class="material-symbols-outlined">arrow_forward</span>
				</button>
				<p class="font-label-md text-on-surface-variant">
					{{ completedAssignments }}/{{ totalGuests }} guests assigned
				</p>
			</div>
		</div>

		<div
			v-if="isDateTimeModalOpen && modalAssignment"
			class="fixed inset-0 z-50 flex items-center justify-center p-4"
		>
			<div class="absolute inset-0 bg-black/40" @click="closeDateTimeModal"></div>
			<div
				class="relative w-full max-w-4xl rounded-2xl bg-white custom-shadow overflow-hidden"
			>
				<div
					class="flex items-center justify-between px-6 py-5 border-b border-outline-variant/20"
				>
					<div>
						<h2 class="font-headline-sm text-headline-sm text-on-surface">
							Select Date & Time
						</h2>
						<p class="font-body-sm text-on-surface-variant">
							{{ modalAssignment.service_name }} for
							{{
								modalAssignment.guest_full_name ||
								`Guest ${modalAssignment.guest_index + 1}`
							}}
						</p>
					</div>
					<button
						class="w-10 h-10 rounded-full hover:bg-surface-container-low flex items-center justify-center"
						@click="closeDateTimeModal"
					>
						<span class="material-symbols-outlined text-on-surface-variant"
							>close</span
						>
					</button>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] min-h-[420px]">
					<div
						class="p-6 border-b lg:border-b-0 lg:border-r border-outline-variant/20 bg-surface-container-lowest"
					>
						<p class="font-label-md text-on-surface mb-4">Choose a date</p>
						<AppointmentDateSelector
							:dates="modalAssignment.available_dates || []"
							:selected-date="modalAssignment.selected_date"
							:loading="isLoadingDates(modalAssignment.id)"
							@select="onSelectDate(modalAssignment.id, $event)"
						/>
					</div>
					<div class="p-6">
						<p class="font-label-md text-on-surface mb-4">Choose a time slot</p>
						<AppointmentSlotSelector
							:slots="modalAssignment.available_slots || []"
							:selected-slot-id="modalAssignment.selected_slot_id"
							:loading="
								isLoadingSlots(modalAssignment.id) ||
								isSavingAssignment(modalAssignment.id)
							"
							@select="onSelectSlot(modalAssignment.id, $event)"
						/>
					</div>
				</div>
			</div>
		</div>
	</main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useBookingWorkflow } from "@/composables/useBookingWorkflow";
import AppointmentDateSelector from "@/components/booking/AppointmentDateSelector.vue";
import AppointmentSlotSelector from "@/components/booking/AppointmentSlotSelector.vue";

const router = useRouter();
const pageLoading = ref(true);
const pageError = ref("");
const expandedGuests = ref<Record<string, boolean>>({});
const expandedServices = ref<Record<string, boolean>>({});
const isDateTimeModalOpen = ref(false);
const modalAssignmentId = ref("");

const {
	draftBooking,
	assignments,
	activeAssignment,
	activeAssignmentIndex,
	totalGuests,
	completedAssignments,
	isWorkflowComplete,
	startWorkflow,
	setActiveAssignment,
	assignGuest,
	loadDates,
	chooseDate,
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

const modalAssignment = computed(
	() => assignments.value.find((assignment) => assignment.id === modalAssignmentId.value) || null
);

function isAssignmentComplete(assignment: any) {
	return (
		assignment.status === "completed" ||
		Boolean(assignment.selected_date && assignment.selected_slot_id)
	);
}

function canCollapseGuest(assignment: any) {
	return isAssignmentComplete(assignment);
}

function serviceCompleted(service: { assignments: Array<any> }) {
	return service.assignments.filter((assignment) => isAssignmentComplete(assignment)).length;
}

function isServiceComplete(service: { assignments: Array<any> }) {
	return (
		service.assignments.length > 0 && serviceCompleted(service) === service.assignments.length
	);
}

function isGuestExpanded(assignmentId: string) {
	return expandedGuests.value[assignmentId] !== false;
}

function isServiceExpanded(serviceKey: string) {
	return expandedServices.value[serviceKey] !== false;
}

function guestSummary(assignment: any) {
	if (assignment.selected_date && assignment.selected_slot) {
		return `${assignment.selected_date} • ${formatTime(assignment.selected_slot.startTime)}`;
	}
	if (assignment.guest_full_name) {
		return assignment.guest_email || "Date & time pending";
	}
	return "Guest details pending";
}

function formatTime(time: string) {
	if (!time) return "";
	try {
		const [hours, minutes] = time.split(":");
		const date = new Date();
		date.setHours(Number(hours), Number(minutes));
		return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
	} catch {
		return time;
	}
}

async function ensureDatesLoaded(assignmentId: string) {
	const assignment = assignments.value.find((item) => item.id === assignmentId);
	if (!assignment) return;
	if (Array.isArray(assignment.available_dates) && assignment.available_dates.length) return;
	await loadDates(assignmentId);
}

function syncExpansionState() {
	const nextGuests: Record<string, boolean> = {};
	const nextServices: Record<string, boolean> = {};

	serviceGroups.value.forEach((service) => {
		nextServices[service.serviceKey] =
			expandedServices.value[service.serviceKey] ?? !isServiceComplete(service);
		service.assignments.forEach((assignment) => {
			nextGuests[assignment.id] =
				expandedGuests.value[assignment.id] ?? !canCollapseGuest(assignment);
		});
	});

	expandedGuests.value = nextGuests;
	expandedServices.value = nextServices;
}

async function focusAssignment(assignmentId: string, globalIndex: number) {
	setActiveAssignment(globalIndex);
	expandedGuests.value = { ...expandedGuests.value, [assignmentId]: true };
	const assignment = assignments.value.find((item) => item.id === assignmentId);
	if (assignment) {
		expandedServices.value = { ...expandedServices.value, [assignment.service_key]: true };
	}
	await ensureDatesLoaded(assignmentId);
}

async function toggleGuestCard(assignmentId: string, globalIndex: number) {
	const assignment = assignments.value.find((item) => item.id === assignmentId);
	if (!assignment) return;

	setActiveAssignment(globalIndex);
	if (!canCollapseGuest(assignment)) {
		expandedGuests.value = { ...expandedGuests.value, [assignmentId]: true };
		return;
	}

	const isExpanded = isGuestExpanded(assignmentId);
	expandedGuests.value = { ...expandedGuests.value, [assignmentId]: !isExpanded };
	if (!isExpanded) {
		await ensureDatesLoaded(assignmentId);
	}
}

function toggleService(serviceKey: string) {
	const service = serviceGroups.value.find((item) => item.serviceKey === serviceKey);
	if (!service || !isServiceComplete(service)) return;
	expandedServices.value = {
		...expandedServices.value,
		[serviceKey]: !isServiceExpanded(serviceKey),
	};
}

async function initializePage() {
	pageLoading.value = true;
	pageError.value = "";
	try {
		await startWorkflow();
		syncExpansionState();
		if (activeAssignment.value) {
			await focusAssignment(activeAssignment.value.id, activeAssignmentIndex.value);
		}
	} catch (error: any) {
		pageError.value = error?.message || "Unable to initialize booking workflow.";
	} finally {
		pageLoading.value = false;
	}
}

function onAssignGuest(
	assignmentId: string,
	payload: { fullName: string; email?: string; mobile?: string }
) {
	assignGuest(assignmentId, payload);
	if (activeAssignment.value?.id !== assignmentId) {
		const assignment = assignments.value.find((item) => item.id === assignmentId);
		if (!assignment) return;
		const service = serviceGroups.value.find(
			(group) => group.serviceKey === assignment.service_key
		);
		const activeIndex = service?.assignments.find(
			(item) => item.id === assignmentId
		)?.globalIndex;
		if (typeof activeIndex === "number") {
			setActiveAssignment(activeIndex);
		}
	}
}

async function openDateTimeModal(assignmentId: string, globalIndex: number) {
	await focusAssignment(assignmentId, globalIndex);
	modalAssignmentId.value = assignmentId;
	isDateTimeModalOpen.value = true;
}

function closeDateTimeModal() {
	isDateTimeModalOpen.value = false;
	modalAssignmentId.value = "";
}

async function onSelectDate(assignmentId: string, date: string) {
	try {
		await chooseDate(assignmentId, date);
	} catch (error) {
		console.error("[BookingWorkflow] Date selection failed:", error);
	}
}

async function onSelectSlot(assignmentId: string, slotId: string) {
	const assignment = assignments.value.find((item) => item.id === assignmentId);
	if (!assignment) return;

	chooseSlot(assignmentId, slotId);
	try {
		await confirmAssignment(assignmentId);
		expandedGuests.value = { ...expandedGuests.value, [assignmentId]: false };
		syncExpansionState();

		const refreshed = assignments.value.find((item) => item.id === assignmentId);
		if (refreshed?.service_key) {
			const service = serviceGroups.value.find(
				(group) => group.serviceKey === refreshed.service_key
			);
			if (service && isServiceComplete(service)) {
				expandedServices.value = {
					...expandedServices.value,
					[refreshed.service_key]: false,
				};
			}
		}

		closeDateTimeModal();
		const nextPendingIndex = assignments.value.findIndex(
			(item) => !isAssignmentComplete(item)
		);
		if (nextPendingIndex >= 0) {
			const nextAssignment = assignments.value[nextPendingIndex];
			await focusAssignment(nextAssignment.id, nextPendingIndex);
		}
	} catch (error) {
		console.error("[BookingWorkflow] Slot selection failed:", error);
	}
}

async function proceedToPayment() {
	if (!isWorkflowComplete.value || !draftBooking.value?.id) {
		pageError.value = "Complete all assignments before continuing to payment.";
		return;
	}

	await router.push({
		name: "ReviewPricing",
		params: { bookingId: draftBooking.value.id },
	});
}

onMounted(() => {
	initializePage();
});

watch(
	() =>
		assignments.value.map(
			(assignment) =>
				`${assignment.id}:${assignment.status}:${assignment.selected_slot_id || ""}`
		),
	() => {
		syncExpansionState();
	}
);

watch(
	() => activeAssignment.value?.id,
	async (newAssignmentId) => {
		if (!newAssignmentId) return;
		try {
			await ensureDatesLoaded(newAssignmentId);
		} catch (error) {
			console.error(`Failed to load dates for assignment ${newAssignmentId}:`, error);
		}
	}
);
</script>
