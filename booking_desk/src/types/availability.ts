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
}

export interface CoupleSlotLeg {
  provider: string;
  providerName: string;
  serviceUnit?: string | null;
  serviceUnitName?: string | null;
  startTime: string;
  endTime: string;
  duration: number;
  bufferBefore: number;
  bufferAfter: number;
  slotIds: string[];
}

export interface CoupleAvailableSlot {
  id: string;
  candidateId: string;
  date: string;
  startTime: string;
  guest1: CoupleSlotLeg;
  guest2: CoupleSlotLeg;
  provider1: string;
  provider2: string;
  providerSummary: string;
  availability: SlotAvailability;
  isCouple: true;
}
