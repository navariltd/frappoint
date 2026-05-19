import {
	fetchOfflinePaymentMethodsApi,
	fetchOnlinePaymentGatewaysApi,
} from "@/api/paymentMethods.api";

const toLower = (value) => String(value || "").toLowerCase();

function inferOfflineDetails(method = {}) {
	const label = toLower(method.label || method.modeOfPayment);
	if (label.includes("cash")) return "Counter cash settlement";
	if (label.includes("bank")) return "Bank transfer settlement";
	if (label.includes("card") || label.includes("pos")) return "Card/POS settlement";
	return "Manual settlement";
}

function inferOnlineCapabilities(method = {}) {
	if (Array.isArray(method.capabilities) && method.capabilities.length) {
		return method.capabilities;
	}

	const label = toLower(method.label || method.gateway);
	if (label.includes("mpesa") || label.includes("m-pesa")) {
		return ["mpesa", "link"];
	}

	return ["redirect", "link"];
}

function inferGatewayType(method = {}) {
	if (method.providerType) return method.providerType;
	const label = toLower(method.label || method.gateway);
	if (label.includes("mpesa") || label.includes("m-pesa")) return "mpesa";
	return "hosted";
}

export function normalizeOfflineMethod(raw = {}) {
	return {
		id: raw.id || "",
		type: "offline",
		name: raw.label || raw.modeOfPayment || "Offline Payment",
		details: inferOfflineDetails(raw),
		sourceType: raw.sourceType || "mode_of_payment",
		providerType: raw.providerType || "manual",
		modeOfPayment: raw.modeOfPayment || "",
		gateway: "",
		gatewayType: "",
		capabilities: [],
		label: raw.label || raw.modeOfPayment || "Offline Payment",
	};
}

export function normalizeOnlineMethod(raw = {}) {
	return {
		id: raw.id || "",
		type: "online",
		name: raw.label || raw.gateway || "Online Payment",
		sourceType: raw.sourceType || "gateway",
		providerType: raw.providerType || inferGatewayType(raw),
		gatewayType: inferGatewayType(raw),
		capabilities: inferOnlineCapabilities(raw),
		gateway: raw.gateway || "",
		modeOfPayment: "",
		details: "",
		label: raw.label || raw.gateway || "Online Payment",
	};
}

export async function fetchOfflinePaymentMethods(bookingId) {
	const payload = await fetchOfflinePaymentMethodsApi(bookingId);
	const methods = Array.isArray(payload?.methods)
		? payload.methods.map(normalizeOfflineMethod)
		: [];
	const defaultMethodId = payload?.defaultMethodId || methods[0]?.id || "";

	return {
		methods,
		defaultMethodId,
	};
}

export async function fetchOnlinePaymentGateways(bookingId) {
	const payload = await fetchOnlinePaymentGatewaysApi(bookingId);
	const methods = Array.isArray(payload?.methods)
		? payload.methods.map(normalizeOnlineMethod)
		: [];
	const defaultMethodId = payload?.defaultMethodId || methods[0]?.id || "";

	return {
		methods,
		defaultMethodId,
	};
}
