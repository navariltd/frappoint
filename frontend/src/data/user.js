import router from "@/router";
import { createResource } from "frappe-ui";
import { defineStore } from "pinia";

export const userResource = createResource({
	url: "frappe.auth.get_logged_user",
	cache: "User",
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			router.push({ name: "LoginPage" });
		}
	},
});

export const useUserStore = defineStore("user", () => {
	let userDocResource = createResource({
		url: "frappoint.frappoint.api.user.get_user_details",
		onError(error) {
			if (error && error.exc_type === "AuthenticationError") {
				router.push("/login");
			}
		},
		auto: true,
	});
	return {
		userDocResource,
	};
});
