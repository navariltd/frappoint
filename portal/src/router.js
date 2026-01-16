import { userResource } from "@/data/user";
import { createRouter, createWebHistory } from "vue-router";
import { session } from "./data/session";

const routes = [
	{
		path: "/",
		name: "Services",
		component: () => import("@/pages/Services.vue"),
		meta: { requiresLogin: false },
	},
	{
		path: "/services/:name",
		name: "ServiceDetails",
		component: () => import("@/pages/ServiceDetails.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "Login",
		path: "/login",
		component: () => import("@/pages/Login.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "Bookings",
		path: "/bookings",
		component: () => import("@/pages/Bookings.vue"),
		meta: { requiresLogin: true },
	},
];

const router = createRouter({
	history: createWebHistory("/portal"),
	routes,
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn = session.isLoggedIn;
	try {
		await userResource.promise;
	} catch (error) {
		isLoggedIn = false;
	}

	if (to.meta.requiresLogin && !isLoggedIn) {
		next({ name: "Login" });
	} else if (to.name === "Login" && isLoggedIn) {
		next({ name: "Home" });
	} else {
		next();
	}
});

export default router;
