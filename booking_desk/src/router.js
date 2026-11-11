import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";
import { HOTEL, SERVICES, useWorkspaceStore } from "./stores/workspace.store";
import { navigateTo } from "./utils";

const routes = [
	{
		// Sends each user to their workspace's home page (see the guard below).
		name: "Home",
		path: "/",
		meta: { requiresLogin: true },
	},
	{
		name: "Dashboard",
		path: "/today",
		component: () => import("@/pages/dashboard/Dashboard.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		path: "/services",
		name: "Services",
		component: () => import("@/pages/services/Services.vue"),
		meta: { requiresLogin: false, workspace: SERVICES },
	},
	{
		name: "Login",
		path: "/login",
		meta: { external: true },
	},
	{
		name: "NewBooking",
		path: "/new_booking",
		component: () => import("@/pages/services/Services.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "GuestAssignment",
		path: "/guest_assignment",
		component: () => import("@/pages/booking/GuestAssignment.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "Checkout",
		path: "/checkout",
		component: () => import("@/components/booking/checkout/Checkout.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "Bookings",
		path: "/bookings",
		component: () => import("@/pages/bookings/Bookings.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "BookingDetails",
		path: "/bookings/:bookingId",
		component: () => import("@/pages/bookings/BookingDetails.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "AppointmentDetails",
		path: "/appointments/:appointmentId",
		component: () => import("@/pages/bookings/AppointmentDetails.vue"),
		meta: { requiresLogin: true, workspace: SERVICES },
	},
	{
		name: "FrontDeskToday",
		path: "/hotel/front-desk",
		component: () => import("@/pages/hotel/FrontDeskToday.vue"),
		meta: { requiresLogin: true, workspace: HOTEL },
	},
	{
		name: "HotelStay",
		path: "/hotel/reservations/:stayId",
		component: () => import("@/pages/hotel/ReservationStay.vue"),
		meta: { requiresLogin: true, workspace: HOTEL },
	},
	{
		name: "HotelBookings",
		path: "/hotel/bookings",
		component: () => import("@/pages/hotel/HotelBookings.vue"),
		meta: { requiresLogin: true, workspace: HOTEL },
	},
	{
		name: "NewReservation",
		path: "/hotel/reservations/new",
		component: () => import("@/pages/hotel/NewReservation.vue"),
		meta: { requiresLogin: true, workspace: HOTEL },
	},
	{
		name: "HotelBooking",
		path: "/hotel/bookings/:bookingId",
		component: () => import("@/pages/hotel/HotelBooking.vue"),
		meta: { requiresLogin: true, workspace: HOTEL },
	},
	{
		name: "Forbidden",
		path: "/forbidden",
		component: () => import("@/pages/Forbidden.vue"),
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

	// The services catalog is public; everything else needs a login.
	if (!auth.isLoggedIn) {
		if (to.meta.requiresLogin) {
			navigateTo("Login", { redirect: `booking_desk${to.fullPath}` });
			return false;
		}
		return true;
	}

	const workspace = useWorkspaceStore();
	await workspace.ready();
	const home = workspace.available.length ? workspace.homeRoute() : { name: "Forbidden" };

	if (to.name === "Home" || to.name === "Login") return home;
	if (to.name === "Forbidden") return true;

	// A page belongs to one workspace; users without that workspace can't open it.
	if (to.meta.workspace && !workspace.can(to.meta.workspace)) return { name: "Forbidden" };
	if (to.meta.workspace) workspace.setActive(to.meta.workspace);
	return true;
});

export default router;
