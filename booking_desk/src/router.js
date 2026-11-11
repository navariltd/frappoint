import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";
import { navigateTo } from "./utils";

const routes = [
	{
		name: "Dashboard",
		path: "/",
		component: () => import("@/pages/dashboard/Dashboard.vue"),
		meta: { requiresLogin: true, requiresServiceProvider: true },
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
		component: () => import("@/pages/services/Services.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "GuestAssignment",
		path: "/guest_assignment",
		component: () => import("@/pages/booking/GuestAssignment.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "Checkout",
		path: "/checkout",
		component: () => import("@/components/booking/checkout/Checkout.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "Bookings",
		path: "/bookings",
		component: () => import("@/pages/bookings/Bookings.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "BookingDetails",
		path: "/bookings/:bookingId",
		component: () => import("@/pages/bookings/BookingDetails.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "AppointmentDetails",
		path: "/appointments/:appointmentId",
		component: () => import("@/pages/bookings/AppointmentDetails.vue"),
		meta: { requiresLogin: true },
	},
	{
		name: "FrontDeskToday",
		path: "/hotel/front-desk",
		component: () => import("@/pages/hotel/FrontDeskToday.vue"),
		meta: { requiresLogin: true, hotel: true },
	},
	{
		name: "HotelStay",
		path: "/hotel/reservations/:stayId",
		component: () => import("@/pages/hotel/ReservationStay.vue"),
		meta: { requiresLogin: true, hotel: true },
	},
	{
		name: "HotelBookings",
		path: "/hotel/bookings",
		component: () => import("@/pages/hotel/HotelBookings.vue"),
		meta: { requiresLogin: true, hotel: true },
	},
	{
		name: "NewReservation",
		path: "/hotel/reservations/new",
		component: () => import("@/pages/hotel/NewReservation.vue"),
		meta: { requiresLogin: true, hotel: true },
	},
	{
		name: "HotelBooking",
		path: "/hotel/bookings/:bookingId",
		component: () => import("@/pages/hotel/HotelBooking.vue"),
		meta: { requiresLogin: true, hotel: true },
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

	if (to.meta.requiresLogin && !auth.isLoggedIn) {
		navigateTo("Login", { redirect: `booking_desk${to.fullPath}` });
		return false;
	}

	if (to.name === "Login" && auth.isLoggedIn) {
		return { name: "Dashboard" };
	}

	// Hotel pages are for hospitality roles; the hotel APIs check property access and permissions.
	if (to.meta.hotel) {
		return auth.canUseHotelDesk || to.name === "Forbidden" ? true : { name: "Forbidden" };
	}

	// Hotel staff without appointment access land on the front desk.
	if (to.name === "Dashboard" && !auth.canAccessDashboard && auth.canUseHotelDesk) {
		return { name: "FrontDeskToday" };
	}

	// Check for Service Provider permission on protected routes
	if (to.meta.requiresServiceProvider && !auth.canAccessDashboard) {
		if (to.name !== "Forbidden") {
			return { name: "Forbidden" };
		}
	}

	if (
		auth.isLoggedIn &&
		!auth.canAccessDashboard &&
		to.name !== "Forbidden" &&
		to.name !== "Login"
	) {
		return { name: "Forbidden" };
	}
});

export default router;
