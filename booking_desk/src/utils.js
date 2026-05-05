import router from "./router";

export function navigateTo(routeName, params = {}) {
	if (routeName === "Login") {
		const redirect = params.redirect || "/booking_desk";
		window.location.href = `/login?redirect-to=${encodeURIComponent(redirect)}`;
		return;
	}

	return router.push({ name: routeName, ...params });
}
