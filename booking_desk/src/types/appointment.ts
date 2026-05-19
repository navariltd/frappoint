export type AppointmentStatus =
	| "active"
	| "arrived"
	| "delayed"
	| "unavailable";

export interface TimelineProvider {
	id: string;
	name: string;
	initials: string;
	designation: string;
	overloaded: boolean;
}

export interface TimelineAppointment {
	id: string;
	providerId: string;
	guestName: string;
	service: string;
	startTime: string;
	duration: number;
	status: AppointmentStatus;
	delayed?: string;
	showTimer?: boolean;
	date: string;
}
