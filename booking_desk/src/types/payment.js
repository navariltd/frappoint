export const PAYMENT_TYPES = {
	FULL: "full",
	DEPOSIT: "deposit",
};

export const PAYMENT_PROGRESS = {
	IDLE: "idle",
	PROCESSING: "processing",
	AWAITING_CONFIRMATION: "awaiting_confirmation",
	SUCCESS: "success",
	FAILED: "failed",
	TIMEOUT: "timeout",
};

export const PAYMENT_METHOD_TYPES = {
	GATEWAY: "gateway",
	MODE_OF_PAYMENT: "mode_of_payment",
};

export const PAYMENT_CHANNELS = {
	OFFLINE: "offline",
	ONLINE: "online",
};

export function createEmptyPaymentMethod() {
	return {
		id: "",
		type: "",
		name: "",
		label: "",
		sourceType: "",
		providerType: "",
		details: "",
		gatewayType: "",
		capabilities: [],
		gateway: "",
		modeOfPayment: "",
	};
}
