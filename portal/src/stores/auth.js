import { defineStore } from "pinia";
import router from "@/router";
import { createResource } from "frappe-ui";

function getSessionUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
	let user = cookies.get("user_id");
	if (!user || user === "Guest") {
		return null;
	}

	return {
		user,
		userName: cookies.get("full_name") || null,
		userImage: cookies.get("user_image") || null,
	};
}

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: getSessionUser(),
		checked: false,
		loading: false,
	}),

	getters: {
		isLoggedIn: (state) => !!state.user,
		userId: (state) => state.user?.user || null,
		userName: (state) => state.user?.userName || null,
		userImage: (state) => state.user?.userImage || null,
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
			this.user = getSessionUser();
		},
	},
});
