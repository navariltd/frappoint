import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";
import { navigateTo } from "./utils";

const routes = [
	{
		name: "Dashboard",
		path: "/",
		component: () => import("@/pages/dashboard/Dashboard.vue"),
		meta: { requiresLogin: true },
	},
	{
		path: "/services",
		name: "Services",
		component: () => import("@/pages/services/Services.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "Login",
		path: "/login",
		meta: { external: true },
	},
	{
		name: "NewBooking",
		path: "/new_booking",
		component: () => import("@/pages/booking/NewBooking.vue"),
		meta: { requiresLogin: true },
	},
];

const router = createRouter({
	history: createWebHistory("/booking_desk"),
	routes,
});

router.beforeEach(async (to) => {
	const auth = useAuthStore();

	await auth.refreshUser?.();

	if (to.meta.requiresLogin && !auth.isLoggedIn) {
		navigateTo("Login", { redirect: `booking_desk${to.fullPath}` });
		return false;
	}

	if (to.name === "Login" && auth.isLoggedIn) {
		return { name: "Dashboard" };
	}
});

export default router;
