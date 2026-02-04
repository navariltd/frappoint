import { ref } from "vue";

export function useAlert() {
	const alertOptions = ref({
		title: "",
		message: "",
		variant: "solid",
		theme: "green",
	});

	function showAlert(title, message, theme = "green") {
		alertOptions.value = {
			title,
			message,
			variant: "solid",
			theme,
		};

		setTimeout(() => {
			alertOptions.value = { ...alertOptions.value, message: "" };
		}, 3000);
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
