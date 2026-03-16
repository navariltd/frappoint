frappe.pages["booking"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Frappoint Booking Desk",
		single_column: true,
	});

	page.set_primary_action(" + New Appointment", () => {
		console.log("Creating A New Appointment");
	});
};
