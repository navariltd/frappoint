export interface ServicePackage {
	id: string;
	name: string;
	amount: number;
	duration: number | null;
	currency: string;
	pricingModel: string;
	guestCount: number | null;
}

export interface ServiceItem {
	id: string;
	name: string;
	description: string;
	duration: number;
	price: number;
	currency: string;
	category: string;
	isActive: boolean;
	defaultPackageId: string;
	availablePrices: ServicePackage[];
	hasMultiplePrices: boolean;
}

export interface ServiceCategory {
	name: string;
}

export interface CartService {
	serviceId: string;
	cartKey: string;
	name: string;
	duration: number;
	price: number;
	currency: string;
	category: string;
	packageName?: string | null;
	packageId?: string | null;
	quantity: number;
}

export interface ServicePackageResolution {
	serviceId: string;
	packages: ServicePackage[];
	defaultPackage: ServicePackage | null;
	providers: unknown[];
	paymentGateways: unknown[];
	minGuests: number | null;
	maxGuests: number | null;
}
