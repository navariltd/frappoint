export type SlotAvailability = "available" | "partial" | "unavailable";

export interface AvailableDate {
	date: string;
	label: string;
}

export interface AvailableSlotProvider {
	provider: string;
	providerName: string;
	serviceUnit?: string | null;
	serviceUnitName?: string | null;
	slotIds: string[];
}

export interface AvailableSlot {
	id: string;
	date: string;
	startTime: string;
	endTime: string;
	duration: number;
	availability: SlotAvailability;
	providers: AvailableSlotProvider[];
	providerSummary: string;
	slotIds: string[];
}