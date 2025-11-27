import router from "@/router";
import { createResource } from "frappe-ui";
import { computed, reactive, ref } from "vue";
import { defineStore } from "pinia";
import { userResource, useUserStore } from "./user";

// TODO: Remove once sessionStore is functional
export function sessionUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
	let _sessionUser = cookies.get("user_id");
	if (_sessionUser === "Guest") {
		_sessionUser = null;
	}
	return _sessionUser;
}

// TODO: Remove once sessionStore is functional
export const session = reactive({
	login: createResource({
		url: "login",
		makeParams({ email, password }) {
			return {
				usr: email,
				pwd: password,
			};
		},
		onSuccess(data) {
			userResource.reload();
			session.user = sessionUser();
			session.login.reset();
			router.replace(data.default_route || "/");
		},
	}),
	logout: createResource({
		url: "logout",
		onSuccess() {
			userResource.reset();
			session.user = sessionUser();
			router.replace({ name: "Login" });
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
});

export const sessionStore = defineStore("frappoint-session", () => {
	let { userDocResource } = useUserStore();

	function sessionUser() {
		const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
		let _sessionUser = cookies.get("user_id");
		if (_sessionUser === "Guest") {
			_sessionUser = null;
		}
		return _sessionUser;
	}

	let user = ref(sessionUser());
	const isLoggedIn = computed(() => !!user.value);

	const login = createResource({
		url: "login",
		onError() {
			throw new Error("Session store: Invalid email or password");
		},
		onSuccess() {
			userDocResource.reload();
			user.value = sessionUser();
			login.reset();
			router.replace({ path: "/" });
		},
	});

	const logout = createResource({
		url: "logout",
		onSuccess() {
			userDocResource.reset();
			user.value = null;
			window.location.reload();
		},
		onError() {
			throw new Error("Session store: Logout failed");
		},
	});

	return {
		user,
		isLoggedIn,
		login,
		logout,
	};
});
