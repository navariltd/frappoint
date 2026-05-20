import { defineStore } from "pinia";
import type { CartItem } from "./bookingCart.store";
import {
	createDraftServiceBooking,
	fetchNormalizedAvailableDates,
	fetchNormalizedAvailableSlots,
	reloadDraftServiceBooking,
	type AvailableDate,
	type AvailableSlot,
	upsertDraftServiceAppointment,
	validateSlotAvailability,
} from "@/services/bookingWorkflow.service";

export interface GuestAssignment {
	id: string;
	service_key: string;
	service_type: string;
	service_name: string;
	package_name: string;
	package_id?: string;
	duration_minutes: number;
	price: number;
	currency: string;
	guest_index: number;
	guest_full_name: string;
	guest_email: string;
	guest_mobile: string;
	selected_date: string;
	available_dates: AvailableDate[];
	selected_slot_id?: string;
	selected_slot?: AvailableSlot;
	available_slots: AvailableSlot[];
	appointment_id?: string;
	status: "pending" | "date_selected" | "slot_selected" | "completed";
}

export interface DraftBookingSession {
	id: string;
	name?: string;
	customer?: string;
	customer_name?: string;
	customer_email?: string;
	customer_mobile?: string;
	total_guests: number;
	currency: string;
	subtotal: number;
	total: number;
	status: string;
	cart_items_snapshot: CartItem[];
}

const STORAGE_KEY = "frappoint-booking-workflow";

const createInitialState = () => ({
	draftBooking: null as DraftBookingSession | null,
	assignments: [] as GuestAssignment[],
	activeAssignmentIndex: -1,
	isCreatingBooking: false,
	isLoadingDatesByAssignment: {} as Record<string, boolean>,
	isLoadingSlotsByAssignment: {} as Record<string, boolean>,
	isSavingAssignmentById: {} as Record<string, boolean>,
	bookingError: "",
	assignmentErrors: {} as Record<string, string>,
	hasHydrated: false,
});

const normalizeHydratedAssignment = (raw: any): GuestAssignment => ({
	id: raw?.id || "",
	service_key: raw?.service_key || `${raw?.service_type || ""}::${raw?.package_name || ""}`,
	service_type: raw?.service_type || "",
	service_name: raw?.service_name || "",
	package_name: raw?.package_name || "",
	package_id: raw?.package_id,
	duration_minutes: Number(raw?.duration_minutes || 0),
	price: Number(raw?.price || 0),
	currency: raw?.currency || "KES",
	guest_index: Number(raw?.guest_index || 0),
	guest_full_name: raw?.guest_full_name || "",
	guest_email: raw?.guest_email || "",
	guest_mobile: raw?.guest_mobile || "",
	selected_date: raw?.selected_date || "",
	available_dates: Array.isArray(raw?.available_dates) ? raw.available_dates : [],
	selected_slot_id: raw?.selected_slot_id || "",
	selected_slot: raw?.selected_slot,
	available_slots: Array.isArray(raw?.available_slots) ? raw.available_slots : [],
	appointment_id: raw?.appointment_id || "",
	status: raw?.status || "pending",
});

export const useBookingWorkflowStore = defineStore("booking-workflow", {
	state: createInitialState,

	getters: {
		totalGuests(state): number {
			return state.assignments.length;
		},
		completedAssignments(state): number {
			return state.assignments.filter((a) => a.status === "completed").length;
		},
		pendingAssignments(state): number {
			return state.assignments.filter((a) => a.status !== "completed").length;
		},
		progressPercentage(state): number {
			if (!state.assignments.length) return 0;
			const completed = state.assignments.filter((a) => a.status === "completed").length;
			return Math.round((completed / state.assignments.length) * 100);
		},
		isWorkflowComplete(state): boolean {
			return state.assignments.length > 0 && state.assignments.every((a) => a.status === "completed");
		},
		activeAssignment(state): GuestAssignment | null {
			if (state.activeAssignmentIndex < 0 || state.activeAssignmentIndex >= state.assignments.length) {
				return null;
			}
			return state.assignments[state.activeAssignmentIndex];
		},
	},

	actions: {
		initializeFromCart(cartItems: CartItem[]) {
			const assignments: GuestAssignment[] = [];
			let assignmentId = 0;

			for (const item of cartItems) {
				for (let i = 0; i < item.quantity; i += 1) {
					const id = `assignment_${assignmentId}`;
					assignmentId += 1;
					assignments.push({
						id,
						service_key: `${item.service_type}::${item.package_name}`,
						service_type: item.service_type,
						service_name: item.service_name,
						package_name: item.package_name,
						package_id: item.metadata?.package_id || item.metadata?.price_id,
						duration_minutes: Number(item.duration_minutes || 0),
						price: Number(item.price || 0),
						currency: item.currency || "KES",
						guest_index: i,
						guest_full_name: "",
						guest_email: "",
						guest_mobile: "",
						selected_date: "",
						available_dates: [],
						selected_slot_id: "",
						selected_slot: undefined,
						available_slots: [],
						appointment_id: "",
						status: "pending",
					});
				}
			}

			const subtotal = cartItems.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 1), 0);

			this.assignments = assignments;
			this.activeAssignmentIndex = assignments.length ? 0 : -1;
			this.draftBooking = {
				id: "",
				name: "",
				total_guests: assignments.length,
				currency: cartItems[0]?.currency || "KES",
				subtotal,
				total: subtotal,
				status: "Draft",
				cart_items_snapshot: cartItems,
			};
			this.bookingError = "";
			this.assignmentErrors = {};
			this.persistState();
		},

		async createDraftBooking(customer: {
			customer?: string;
			fullName?: string;
			email?: string;
			mobileNo?: string;
		}) {
			if (!this.draftBooking) {
				throw new Error("Booking workflow is not initialized.");
			}

			if (this.draftBooking.id) {
				return this.draftBooking;
			}

			this.isCreatingBooking = true;
			this.bookingError = "";
			try {
				const booking = await createDraftServiceBooking({
					customer,
					cartItems: this.draftBooking.cart_items_snapshot,
				});
				this.draftBooking = {
					id: booking.id,
					name: booking.name,
					customer: booking.customerId,
					customer_name: booking.fullName,
					customer_email: booking.email,
					customer_mobile: booking.mobileNo,
					total_guests: booking.totalGuests,
					currency: booking.currency,
					subtotal: booking.subtotal,
					total: booking.grandTotal,
					status: booking.status,
					cart_items_snapshot: this.draftBooking.cart_items_snapshot,
				};
				this.persistState();
				return this.draftBooking;
			} catch (error: any) {
				this.bookingError = error?.message || "Unable to create booking draft.";
				throw error;
			} finally {
				this.isCreatingBooking = false;
			}
		},

		async reloadDraftBooking() {
			if (!this.draftBooking?.id) return null;

			const booking = await reloadDraftServiceBooking({
				bookingId: this.draftBooking.id,
				cartItems: this.draftBooking.cart_items_snapshot,
				customer: {
					customer: this.draftBooking.customer,
					fullName: this.draftBooking.customer_name,
					email: this.draftBooking.customer_email,
					mobileNo: this.draftBooking.customer_mobile,
				},
			});

			this.draftBooking = {
				id: booking.id,
				name: booking.name,
				customer: booking.customerId,
				customer_name: booking.fullName,
				customer_email: booking.email,
				customer_mobile: booking.mobileNo,
				total_guests: booking.totalGuests,
				currency: booking.currency,
				subtotal: booking.subtotal,
				total: booking.grandTotal,
				status: booking.status,
				cart_items_snapshot: this.draftBooking.cart_items_snapshot,
			};
			this.persistState();
			return this.draftBooking;
		},

		setActiveAssignment(index: number) {
			if (index >= 0 && index < this.assignments.length) {
				this.activeAssignmentIndex = index;
			}
		},

		assignGuest(assignmentId: string, payload: { fullName: string; email?: string; mobile?: string }) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) return;
			assignment.guest_full_name = payload.fullName || "";
			assignment.guest_email = payload.email || "";
			assignment.guest_mobile = payload.mobile || "";
			this.persistState();
		},

		async fetchAvailableDates(assignmentId: string) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) return [];

			console.log(`[BookingStore] Fetching available dates for assignment ${assignmentId}:`, {
				serviceType: assignment.service_type,
				duration: assignment.duration_minutes,
			});

			this.isLoadingDatesByAssignment = {
				...this.isLoadingDatesByAssignment,
				[assignmentId]: true,
			};
			this.clearAssignmentError(assignmentId);
			try {
				const dates = await fetchNormalizedAvailableDates({
					serviceType: assignment.service_type,
					duration: assignment.duration_minutes,
				});
				console.log(`[BookingStore] Fetched ${dates.length} available dates for assignment ${assignmentId}`);
				assignment.available_dates = dates;
				this.persistState();
				return dates;
			} catch (error: any) {
				console.error(`[BookingStore] Error fetching dates for assignment ${assignmentId}:`, error);
				this.setAssignmentError(assignmentId, error?.message || "Unable to load available dates.");
				throw error;
			} finally {
				this.isLoadingDatesByAssignment = {
					...this.isLoadingDatesByAssignment,
					[assignmentId]: false,
				};
			}
		},

		selectDate(assignmentId: string, date: string) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) return;
			console.log(`[BookingStore] Date selected for assignment ${assignmentId}: ${date}`);
			assignment.selected_date = date;
			assignment.selected_slot_id = "";
			assignment.selected_slot = undefined;
			assignment.available_slots = [];
			assignment.status = "date_selected";
			this.persistState();
		},

		async fetchAvailableSlots(assignmentId: string) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment || !assignment.selected_date) return [];

			console.log(`[BookingStore] Fetching available slots for assignment ${assignmentId}:`, {
				serviceType: assignment.service_type,
				duration: assignment.duration_minutes,
				date: assignment.selected_date,
			});

			this.isLoadingSlotsByAssignment = {
				...this.isLoadingSlotsByAssignment,
				[assignmentId]: true,
			};
			this.clearAssignmentError(assignmentId);
			try {
				const slots = await fetchNormalizedAvailableSlots({
					serviceType: assignment.service_type,
					duration: assignment.duration_minutes,
					date: assignment.selected_date,
				});
				console.log(`[BookingStore] Fetched ${slots.length} available slots for assignment ${assignmentId}`);
				assignment.available_slots = slots;
				this.persistState();
				return slots;
			} catch (error: any) {
				this.setAssignmentError(assignmentId, error?.message || "Unable to load available slots.");
				throw error;
			} finally {
				this.isLoadingSlotsByAssignment = {
					...this.isLoadingSlotsByAssignment,
					[assignmentId]: false,
				};
			}
		},

		selectSlot(assignmentId: string, slotId: string) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) {
				console.warn(`[BookingStore] Assignment not found for slot selection: ${assignmentId}`);
				return;
			}
			const slot = assignment.available_slots.find((item) => item.id === slotId);
			if (!slot) {
				console.warn(`[BookingStore] Slot not found: ${slotId} in assignment ${assignmentId}`);
				return;
			}
			console.log(`[BookingStore] Slot selected for assignment ${assignmentId}: ${slotId} (${slot.startTime} - ${slot.endTime})`);
			assignment.selected_slot_id = slotId;
			assignment.selected_slot = slot;
			assignment.status = "slot_selected";
			this.persistState();
		},

		async createDraftAppointment(assignmentId: string) {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) throw new Error("Assignment not found.");
			if (!this.draftBooking?.id) throw new Error("Draft booking is required first.");
			if (!assignment.guest_full_name) throw new Error("Guest name is required.");
			if (!assignment.selected_date) throw new Error("Appointment date is required.");
			if (!assignment.selected_slot) throw new Error("Appointment slot is required.");

			console.log(`[BookingStore] Creating appointment for assignment ${assignmentId}:`, {
				guestName: assignment.guest_full_name,
				date: assignment.selected_date,
				slotId: assignment.selected_slot_id,
				slotTime: assignment.selected_slot?.startTime,
			});

			this.isSavingAssignmentById = {
				...this.isSavingAssignmentById,
				[assignmentId]: true,
			};
			this.clearAssignmentError(assignmentId);
			try {
				console.log(`[BookingStore] Validating slot availability for slot IDs:`, assignment.selected_slot.slotIds);
				const slotValidation = await validateSlotAvailability(assignment.selected_slot.slotIds || []);
				console.log(`[BookingStore] Slot validation result:`, slotValidation);
				if (!slotValidation.available) {
					throw new Error("Selected slot is no longer available. Please choose another slot.");
				}

				const result = await upsertDraftServiceAppointment({
					bookingId: this.draftBooking.id,
					appointmentId: assignment.appointment_id || undefined,
					service: {
						serviceKey: assignment.service_key,
						serviceId: assignment.service_type,
						serviceName: assignment.service_name,
						packageName: assignment.package_name,
						packageId: assignment.package_id,
						price: assignment.price,
						currency: assignment.currency,
						duration: assignment.duration_minutes,
					},
					guest: {
						fullName: assignment.guest_full_name,
						email: assignment.guest_email,
						mobileNo: assignment.guest_mobile,
					},
					date: assignment.selected_date,
					slot: assignment.selected_slot,
				});

				console.log(`[BookingStore] Appointment creation succeeded:`, {
					appointmentName: result.appointment?.name,
					bookingId: result.booking?.id,
				});

				assignment.appointment_id = result.appointment?.name || assignment.appointment_id;
				assignment.status = "completed";
				if (result.booking?.id) {
					this.draftBooking = {
						...this.draftBooking,
						id: result.booking.id,
						name: result.booking.name,
						status: result.booking.status,
						subtotal: result.booking.subtotal,
						total: result.booking.grandTotal,
						currency: result.booking.currency,
					};
				}
				console.log(`[BookingStore] Persisting state and moving to next pending assignment...`);
				this.persistState();
				this.moveToNextPending();
				console.log(`[BookingStore] Active assignment index after move: ${this.activeAssignmentIndex}`);
				return result;
			} catch (error: any) {
				this.setAssignmentError(assignmentId, error?.message || "Unable to reserve appointment.");
				throw error;
			} finally {
				this.isSavingAssignmentById = {
					...this.isSavingAssignmentById,
					[assignmentId]: false,
				};
			}
		},

		moveToNextPending() {
			const nextIndex = this.assignments.findIndex((a) => a.status !== "completed");
			console.log(`[BookingStore] Looking for next pending assignment. Current index: ${this.activeAssignmentIndex}, Found: ${nextIndex}`);
			if (nextIndex >= 0) {
				this.activeAssignmentIndex = nextIndex;
				console.log(`[BookingStore] Moved to assignment index ${nextIndex}`);
				return true;
			}
			console.log(`[BookingStore] No more pending assignments. Workflow complete.`);
			return false;
		},

		validateAssignment(assignmentId: string): string[] {
			const assignment = this.assignments.find((item) => item.id === assignmentId);
			if (!assignment) return ["Assignment not found."];
			const issues: string[] = [];
			if (!assignment.guest_full_name) issues.push("Guest is required.");
			if (!assignment.selected_date) issues.push("Date is required.");
			if (!assignment.selected_slot_id) issues.push("Slot is required.");
			return issues;
		},

		setAssignmentError(assignmentId: string, error: string) {
			this.assignmentErrors = { ...this.assignmentErrors, [assignmentId]: error };
		},

		clearAssignmentError(assignmentId: string) {
			const next = { ...this.assignmentErrors };
			delete next[assignmentId];
			this.assignmentErrors = next;
		},

		persistState() {
			if (typeof window === "undefined" || !window.localStorage) return;
			window.localStorage.setItem(
				STORAGE_KEY,
				JSON.stringify({
					draftBooking: this.draftBooking,
					assignments: this.assignments,
					activeAssignmentIndex: this.activeAssignmentIndex,
				})
			);
		},

		hydrateFromStorage() {
			if (this.hasHydrated || typeof window === "undefined" || !window.localStorage) {
				this.hasHydrated = true;
				return;
			}
			try {
				const raw = window.localStorage.getItem(STORAGE_KEY);
				if (raw) {
					const parsed = JSON.parse(raw);
					this.draftBooking = parsed?.draftBooking || null;
					this.assignments = Array.isArray(parsed?.assignments)
						? parsed.assignments.map(normalizeHydratedAssignment)
						: [];
					this.activeAssignmentIndex = parsed?.activeAssignmentIndex ?? -1;
					if (this.activeAssignmentIndex >= this.assignments.length) {
						this.activeAssignmentIndex = this.assignments.length ? 0 : -1;
					}
				}
			} catch {
				this.draftBooking = null;
				this.assignments = [];
				this.activeAssignmentIndex = -1;
			}
			this.hasHydrated = true;
		},

		clearWorkflow() {
			Object.assign(this, createInitialState(), { hasHydrated: true });
			if (typeof window !== "undefined" && window.localStorage) {
				window.localStorage.removeItem(STORAGE_KEY);
			}
		},
	},
});
