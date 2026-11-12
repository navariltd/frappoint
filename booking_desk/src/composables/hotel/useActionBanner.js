import { onBeforeUnmount, ref } from "vue";

/**
 * In-page confirmations and notices for the hotel pages, used instead of the browser's
 * confirm(), prompt() and alert(). Render the state with <ActionBanner>.
 *
 *   const { banner, ask, notify, confirm, cancel } = useActionBanner();
 *   const answer = await ask({ title: "Check out Amina?", confirmLabel: "Check out" });
 *   if (answer) run(() => checkOutApi(stay, answer.reason));
 *
 * `ask` resolves to { reason } when confirmed and to null when cancelled. Give `reasonLabel` to
 * ask for a reason; the confirm button stays disabled until one is typed. A new question or
 * notice replaces one still on screen, which counts as cancelled.
 */
export function useActionBanner() {
	const banner = ref(null);
	let resolve = null;

	function settle(value) {
		const pending = resolve;
		resolve = null;
		banner.value = null;
		pending?.(value);
	}

	function ask(options) {
		settle(null);
		return new Promise((done) => {
			resolve = done;
			banner.value = {
				tone: "warning",
				confirmLabel: "Confirm",
				cancelLabel: "Cancel",
				...options,
				kind: "ask",
			};
		});
	}

	function notify(options) {
		settle(null);
		banner.value = { tone: "info", ...options, kind: "notice" };
	}

	const confirm = (reason = "") => settle({ reason: String(reason).trim() });
	const cancel = () => settle(null);

	// Leaving the page with a question open counts as cancelling it.
	onBeforeUnmount(cancel);

	return { banner, ask, notify, confirm, cancel };
}
