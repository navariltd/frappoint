/**
 * Turn a failed server call into one plain sentence for the person at the desk.
 *
 * Server messages can carry HTML (<p>, <strong>) and internal names ("Function
 * frappoint.….get_rate_grid is not whitelisted"); people should see neither. Known failures get
 * fixed wording; everything else is the server's own message as plain text. The full error stays
 * in the browser console for developers.
 */

const NO_ACCESS =
	"You don't have access to this. Ask a Hospitality Manager or your administrator if you need it.";
const SERVER_FAULT =
	"Something went wrong on our side. Try again, and tell your administrator if it keeps happening.";
const OFFLINE = "Can't reach the server. Check your connection and try again.";
const FALLBACK = "Something went wrong. Please try again.";

const NO_ACCESS_TEXT = /not whitelisted|not permitted to access this resource|login to access/i;
const SERVER_FAULT_TEXT = /^internal server error$/i;
const OFFLINE_TEXT = /failed to fetch|networkerror|load failed/i;
const NO_ACCESS_TYPES = ["PermissionError", "SessionExpired"];

/** Text without markup: "<p>Room <b>101</b></p>" → "Room 101". */
export function plainText(value) {
	if (value == null) return "";
	const text = String(value);
	if (!/[<&]/.test(text)) return text.replace(/\s+/g, " ").trim();
	const doc = new DOMParser().parseFromString(text, "text/html");
	// Block elements end a sentence; keep the words apart when the tags go.
	doc.querySelectorAll("p, div, br, li").forEach((node) => node.append(" "));
	return (doc.body.textContent || "").replace(/\s+/g, " ").trim();
}

function serverMessages(error) {
	let messages = Array.isArray(error?.messages) ? error.messages : [];
	if (!messages.length && error?._server_messages) {
		try {
			messages = JSON.parse(error._server_messages).map((raw) => {
				try {
					return JSON.parse(raw).message;
				} catch {
					return raw;
				}
			});
		} catch {
			messages = [error._server_messages];
		}
	}
	return messages.map(plainText).filter(Boolean);
}

export function readableError(error, fallback = FALLBACK) {
	if (!error) return fallback;
	if (typeof error === "string") return plainText(error) || fallback;

	const messages = serverMessages(error);
	const text = messages.join(" ");
	const status = error?.response?.status;

	if (
		NO_ACCESS_TEXT.test(text) ||
		(!messages.length && NO_ACCESS_TYPES.includes(error.exc_type))
	) {
		return NO_ACCESS;
	}
	if (status >= 500 && (!text || SERVER_FAULT_TEXT.test(text))) return SERVER_FAULT;
	if (text && !SERVER_FAULT_TEXT.test(text)) return text;
	if (OFFLINE_TEXT.test(error.message || "")) return OFFLINE;
	if (SERVER_FAULT_TEXT.test(text)) return SERVER_FAULT;
	// frappe-ui's own message starts with the method name; that is for developers.
	return error.exc_type ? fallback : plainText(error.message) || fallback;
}
