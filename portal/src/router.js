import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";

const routes = [
	{
		path: "/",
		name: "Services",
		component: () => import("@/pages/services/Services.vue"),
		meta: { requiresLogin: false },
	},
	{
		path: "/services/:name",
		name: "ServiceDetails",
		component: () => import("@/pages/services/ServiceDetails.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "Login",
		path: "/login",
		component: () => import("@/pages/auth/Login.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "Signup",
		path: "/signup",
		component: () => import("@/pages/auth/Signup.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "Bookings",
		path: "/bookings",
		component: () => import("@/pages/booking/Bookings.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "User",
		path: "/user/me",
		component: () => import("@/pages/User.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "BookingDetails",
		path: "/book/:serviceType",
		component: () => import("@/pages/booking/BookingDetails.vue"),
		meta: { requiresLogin: false },
	},
	{
		name: "AppointmentDetails",
		path: "/appointments/:id",
		component: () => import("@/pages/booking/AppointmentDetails.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "RescheduleAppointment",
		path: "/appointments/:id/reschedule",
		component: () => import("@/pages/booking/RescheduleAppointment.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "BookingConfirmation",
		path: "/booking/:bookingId",
		component: () => import("@/pages/booking/BookingConfirmation.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "CancelAppointment",
		path: "/appointments/:id/cancel",
		component: () => import("@/pages/booking/CancelAppointment.vue"),
		meta: { requiresLogin: true },
	},
];

const router = createRouter({
	history: createWebHistory("/portal"),
	routes,
});

router.beforeEach(async (to) => {
	const auth = useAuthStore();

	await auth.refreshUser?.();

	if (to.meta.requiresLogin && !auth.isLoggedIn) {
		return { name: "Login" };
	}

	if (to.name === "Login" && auth.isLoggedIn) {
		return { name: "Services" };
	}

	if (to.name === "Signup" && auth.isLoggedIn) {
		return { name: "Services" };
	}
});

export default router;
