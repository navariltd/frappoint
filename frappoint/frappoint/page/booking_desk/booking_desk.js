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
	const page_head = document.querySelector(".page-head");
	if (page_head) page_head.style.display = "none";

	// container for vue
	page.body.append(`<div id="booking-desk"></div>`);

	// load Vue bundle with jQuery first to avoid dom.js errors
	const script = document.createElement("script");
	script.type = "module";
	script.src = "/assets/frappoint/booking_desk/vue-booking-desk.js";
	document.body.appendChild(script);

	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = "/assets/frappoint/booking_desk/vue-booking-desk-index.css";
	document.head.appendChild(link);
};
