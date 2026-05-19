export interface CustomerSummary {
	id: string;
	name: string;
	phone: string;
	email: string;
	recentBookingsCount: number;
	outstandingBalance: number;
	isVip: boolean;
}
