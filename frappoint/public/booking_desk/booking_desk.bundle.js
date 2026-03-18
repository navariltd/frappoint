import { createApp } from "vue";
import Home from "./Home.vue";

function setup_vue($wrapper) {
	const el = $wrapper.get(0);

	const app = createApp(Home);
	app.mount(el);
	return app;
}

frappe.ui.setup_vue = setup_vue;

export default setup_vue;
