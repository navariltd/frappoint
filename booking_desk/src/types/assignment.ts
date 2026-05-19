import type { AvailableDate, AvailableSlot } from "./availability";

export interface AssignedGuest {
	guestKey: string;
	sequence: number;
	customerId: string;
	fullName: string;
	email: string;
	mobileNo: string;
	isInlineGuest: boolean;
	isComplete: boolean;
	date: string;
	slot: AvailableSlot | null;
	availableDates: AvailableDate[];
	availableSlots: AvailableSlot[];
}

export interface ServiceAssignment {
	serviceKey: string;
	serviceId: string;
	serviceName: string;
	packageName: string;
	quantity: number;
	duration: number;
	price: number;
	currency: string;
	guests: AssignedGuest[];
}

export interface AssignmentProgress {
	totalGuests: number;
	completedGuests: number;
	percent: number;
}