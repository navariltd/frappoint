frappe.pages["booking_desk"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Frappoint Booking Desk",
		single_column: true,
		hide_sidebar: true,
	});

	// hide Frappe navbar & topbar
	const sticky = document.querySelector(".sticky-top");
	if (sticky) sticky.style.display = "none";
	const nav = document.querySelector(".navbar");
	if (nav) nav.style.display = "none";

	// container for vue
	page.body.append(`<div id="booking-desk"></div>`);

	// load Vue bundle with jQuery first to avoid dom.js errors
	frappe.require([
		"/assets/frappoint/booking_desk/vue-booking-desk.js",
		"/assets/frappoint/booking_desk/vue-booking-desk-index.css",
	]);
};
