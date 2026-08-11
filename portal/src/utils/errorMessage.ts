function parseMessage(value: unknown): string[] {
	if (!value) return [];

	if (Array.isArray(value)) {
		return value.flatMap(parseMessage);
	}

	if (typeof value === "object") {
		const message = (value as { message?: unknown }).message;
		return message ? parseMessage(message) : [];
	}

	const text = String(value).trim();
	if (!text) return [];

	try {
		const parsed = JSON.parse(text);
		if (parsed !== text) return parseMessage(parsed);
	} catch {
		// The value is already a plain message.
	}

	return [text];
}

function isTechnicalMessage(message: string): boolean {
	return (
		message.includes("/api/method/") ||
		/\b(?:ValidationError|PermissionError|AuthenticationError|Exception)\b/.test(message)
	);
}

/**
 * Extract a customer-facing message from a Frappe request error.
 *
 * frappe-ui sets Error.message to the API method and exception type, while the
 * useful validation copy is stored in `messages` or `_server_messages`.
 */
export function getErrorMessage(error: any, fallback: string): string {
	const candidates = [
		...parseMessage(error?.messages),
		...parseMessage(error?._server_messages),
		...parseMessage(error?._error_message),
		...parseMessage(error?.response?.data?._server_messages),
		...parseMessage(error?.response?.data?._error_message),
		...parseMessage(error?.message),
	];

	return candidates.find((message) => !isTechnicalMessage(message)) || fallback;
}
