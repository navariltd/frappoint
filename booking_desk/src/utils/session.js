/**
 * Keeps the desk working through an expired login.
 *
 * Every server call goes through `sessionAwareRequest` (registered as frappe-ui's resource
 * fetcher in main.js). When a call is refused with 401 or 403 the guard asks the server who is
 * signed in:
 *
 * - Still the same user: the refusal is a real "no access" and goes back to the page as usual.
 * - Nobody: the login has expired. The guard opens the "You've been signed out" dialog and holds
 *   the call, and every call after it. Once the user signs in again, the held calls run again and
 *   the pages finish loading as if nothing happened, keeping whatever was typed.
 *
 * Running a held call again is safe: the server refuses a signed-out request before any of the
 * app's code runs, so nothing was half done.
 *
 * Pages that were opened without a login (the public services catalog) are left alone.
 */
import { frappeRequest } from "frappe-ui";
import { reactive } from "vue";

const WHO_AM_I = "frappe.auth.get_logged_user";
const LOGIN = "login";
const LOGOUT = "logout";
// Calls the guard never holds: signing in and out, and its own check.
const EXEMPT = [WHO_AM_I, LOGIN, LOGOUT];
const AUTH_STATUSES = [401, 403];
// After the tab has been away this long, check the login when the user comes back.
const AWAY_CHECK_MS = 2 * 60 * 1000;

export function cookieUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
	const user = cookies.get("user_id");
	return user && user !== "Guest" ? user : null;
}

export const session = reactive({
	// The user this page was working for. Empty for visitors who never signed in.
	user: cookieUser(),
	expired: false,
});

let pending = []; // { resolve, reject } of calls waiting for the user to sign in again
let check = null; // the one "who is signed in?" request in flight

function exempt(url) {
	return EXEMPT.some((name) => url === name || url?.endsWith(`/${name}`));
}

function authFailure(error) {
	// frappe-ui fills `error.status` from the response text, so it is always empty: read the
	// response itself.
	return AUTH_STATUSES.includes(error?.response?.status);
}

/** Whether the server still has the page's user signed in. Unknown (offline) counts as yes. */
export function stillSignedIn() {
	check ||= frappeRequest({ url: WHO_AM_I })
		.then((user) => !!user && user !== "Guest")
		.catch((error) => !authFailure(error))
		.finally(() => {
			check = null;
		});
	return check;
}

export function markExpired() {
	if (session.user) session.expired = true;
}

function waitForSignIn() {
	return new Promise((resolve, reject) => pending.push({ resolve, reject }));
}

/** The same user signed in again: run every held call. */
export function resume() {
	session.expired = false;
	const waiting = pending;
	pending = [];
	waiting.forEach(({ resolve }) => resolve());
}

/** Someone else is signing in instead: the held calls are dropped with the page. */
export function abandon() {
	const waiting = pending;
	pending = [];
	const error = new Error("Signed out");
	waiting.forEach(({ reject }) => reject(error));
}

export async function sessionAwareRequest(options) {
	try {
		return await frappeRequest(options);
	} catch (error) {
		if (!session.user || exempt(options?.url) || !authFailure(error)) throw error;
		if (!session.expired) {
			if (await stillSignedIn()) throw error;
			markExpired();
		}
		await waitForSignIn();
		return frappeRequest(options);
	}
}

/** Sign in from the dialog. Returns the user now signed in. */
export async function signIn(usr, pwd) {
	await frappeRequest({ url: LOGIN, params: { usr, pwd } });
	return cookieUser();
}

/** Notice an expired login when the user comes back to the tab, before they click anything. */
export function watchForExpiry() {
	let hiddenAt = null;
	document.addEventListener("visibilitychange", async () => {
		if (document.hidden) {
			hiddenAt = Date.now();
			return;
		}
		const away = hiddenAt ? Date.now() - hiddenAt : 0;
		hiddenAt = null;
		if (
			session.user &&
			!session.expired &&
			away >= AWAY_CHECK_MS &&
			!(await stillSignedIn())
		) {
			markExpired();
		}
	});
}
