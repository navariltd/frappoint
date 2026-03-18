frappe.pages["booking_desk"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Frappoint Booking Desk",
		single_column: true,
		hide_sidebar: true,
	});
};

frappe.pages["booking_desk"].on_page_show = (wrapper) => load_vue(wrapper);

async function load_vue(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	await frappe.require("booking_desk.bundle.js");
	frappe.booking_desk_app = frappe.ui.setup_vue($parent);
}
