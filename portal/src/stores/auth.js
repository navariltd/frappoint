import { defineStore } from "pinia";
import router from "@/router";
import { createResource } from "frappe-ui";

function getSessionUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
	let user = cookies.get("user_id");
	let userName = cookies.get("full_name");
	user === "Guest" ? null : user;
	userName === "Guest" ? null : userName;

	return { user, userName };
}

export const useAuthStore = defineStore("auth", {
	state: () => ({
		userId: getSessionUser().user,
		userName: getSessionUser().userName,
		checked: false,
		loading: false,
	}),

	getters: {
		isLoggedIn: (state) => !!state.userId,
	},

	actions: {
		async refreshUser() {
			if (this.checked) return;

			const resource = createResource({
				url: "frappe.auth.get_logged_user",
			});

			try {
				await resource.fetch();
				this.setUser();
			} catch {
				this.userId = null;
			} finally {
				this.checked = true;
			}
		},

		async login(email, password) {
			this.loading = true;

			const loginResource = createResource({
				url: "login",
				makeParams() {
					return { usr: email, pwd: password };
				},
			});

			try {
				const data = await loginResource.submit();
				this.setUser();
				router.replace("/");
			} finally {
				this.loading = false;
			}
		},

		async logout() {
			const logoutResource = createResource({
				url: "logout",
			});

			await logoutResource.submit();
			this.userId = null;
			this.userName = null;
			router.replace({ name: "Login" });
		},

		setUser() {
			this.userId = getSessionUser().user;
			this.userName = getSessionUser().userName;
		},
	},
});
