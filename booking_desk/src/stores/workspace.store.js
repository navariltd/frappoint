import { defineStore } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useHotelStore } from "@/stores/hotel.store";

/**
 * The app has two workspaces: Services (appointments) and Hotel (the PMS). Users see the ones their
 * roles allow; the Hotel workspace also needs hospitality enabled. The sidebar shows one workspace
 * at a time, and a switcher appears only for users who can use both.
 */
export const SERVICES = "services";
export const HOTEL = "hotel";

export const WORKSPACES = {
	[SERVICES]: { key: SERVICES, label: "Services", icon: "spa" },
	[HOTEL]: { key: HOTEL, label: "Hotel", icon: "hotel" },
};

// Hospitality Settings > Default Landing Page -> route. Tape Chart arrives with F16.
const HOTEL_LANDING_ROUTES = {
	"Front Desk Today": "FrontDeskToday",
	Reservations: "HotelBookings",
	"Tape Chart": "FrontDeskToday",
};

const storageKey = (user) => `frappoint.workspace.${user || "guest"}`;

function readSaved(user) {
	try {
		return window.localStorage.getItem(storageKey(user));
	} catch {
		return null;
	}
}

function save(user, workspace) {
	try {
		window.localStorage.setItem(storageKey(user), workspace);
	} catch {
		// Storage blocked: the last workspace just isn't remembered.
	}
}

export const useWorkspaceStore = defineStore("workspace", {
	state: () => ({ active: null }),

	getters: {
		canUseServices: () => useAuthStore().canAccessDashboard,
		canUseHotel: () => useAuthStore().canUseHotelDesk && useHotelStore().enabled,
		available() {
			return [this.canUseHotel && HOTEL, this.canUseServices && SERVICES].filter(Boolean);
		},
		showSwitcher() {
			return this.available.length > 1;
		},
		current() {
			return WORKSPACES[this.active] || null;
		},
	},

	actions: {
		/** Load what decides the workspaces: the user's roles, then hospitality access. */
		async ready() {
			const auth = useAuthStore();
			await auth.refreshUser?.();
			if (auth.canUseHotelDesk) await useHotelStore().load();
			if (!this.active || !this.available.includes(this.active)) {
				const saved = readSaved(auth.userId);
				this.active = this.available.includes(saved) ? saved : this.available[0] || null;
			}
		},

		can(workspace) {
			return this.available.includes(workspace);
		},

		setActive(workspace) {
			if (!this.can(workspace) || this.active === workspace) return;
			this.active = workspace;
			save(useAuthStore().userId, workspace);
		},

		/** The page a workspace opens on. */
		homeRoute(workspace = this.active) {
			if (workspace === HOTEL) {
				return {
					name:
						HOTEL_LANDING_ROUTES[useHotelStore().defaultLandingPage] ||
						"FrontDeskToday",
				};
			}
			if (workspace === SERVICES) return { name: "Dashboard" };
			return { name: "Forbidden" };
		},
	},
});
