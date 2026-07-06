import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { navigateTo } from "@/utils";

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
		permissions: {},
		roles: [],
		checked: false,
		loading: false,
	}),

	getters: {
		isLoggedIn: (state) => !!state.user,
		userId: (state) => state.user?.user || null,
		userName: (state) => state.user?.userName || null,
		userImage: (state) => state.user?.userImage || null,
		canAccessDashboard: (state) => {
			return (
				state.roles?.includes("Service Provider") ||
				state.roles?.includes("System Manager")
			);
		},
	},

	actions: {
		async refreshUser() {
			if (this.checked) return;

			const resource = createResource({
				url: "frappoint.frappoint.api.user.get_user_details",
			});

			try {
				const data = await resource.fetch();
				this.permissions = data.permissions || {};
				this.roles = data.roles || [];
				this.setUser();
			} catch {
				this.user = null;
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
				await loginResource.submit();
				this.setUser();
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
			navigateTo("Login");
		},

		setUser() {
			this.user = getSessionUser();
		},
	},
});
