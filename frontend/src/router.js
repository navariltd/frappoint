import { userResource } from "@/data/user";
import { createRouter, createWebHistory } from "vue-router";
import { session } from "./data/session";

const routes = [
	{
		path: "/",
		name: "Home",
		component: () => import("@/pages/Home.vue"),
	},
	{
		name: "Login",
		path: "/account/login",
		component: () => import("@/pages/Login.vue"),
	},
	{
		name: "Services",
		path: "/services",
		component: () => import("@/pages/Services.vue"),
	},
	{
		name: "Appointments",
		path: "/appointments",
		component: () => import("@/pages/AppointmentPage.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/frappoint"),
	routes,
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn = session.isLoggedIn;
	try {
		await userResource.promise;
	} catch (error) {
		isLoggedIn = false;
	}

	if (to.name === "Login" && isLoggedIn) {
		next({ name: "Home" });
	} else if (to.name !== "Login" && !isLoggedIn) {
		next({ name: "Login" });
	} else {
		next();
	}
});

export default router;
