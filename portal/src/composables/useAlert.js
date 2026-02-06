import { ref } from "vue";

export function useAlert() {
	const alertOptions = ref({
		title: "",
		message: "",
		variant: "solid",
		theme: "green",
	});

	function showAlert(title, message, theme = "green", duration = 5000) {
		alertOptions.value = {
			title,
			message,
			variant: "solid",
			theme,
		};

		// Auto-dismiss after duration
		if (duration > 0) {
			setTimeout(() => {
				alertOptions.value = { ...alertOptions.value, message: "" };
			}, duration);
		}
	}

	function hideAlert() {
		alertOptions.value = { ...alertOptions.value, message: "" };
	}

	return {
		alertOptions,
		showAlert,
		hideAlert,
	};
}
