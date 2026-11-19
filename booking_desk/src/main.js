import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { initSocket } from "./socket";
import { createPinia } from "pinia";
import { initializeBranding } from "./branding";

import { FrappeUI, pageMetaPlugin, setConfig } from "frappe-ui";
import { sessionAwareRequest, watchForExpiry } from "./utils/session";
import "./index.css";

// Every server call: an expired login opens the sign-in dialog and the call waits for it.
setConfig("resourceFetcher", sessionAwareRequest);
watchForExpiry();

async function bootstrap() {
	await initializeBranding();

	const pinia = createPinia();
	const app = createApp(App);

	app.use(pinia);
	app.use(router);
	app.use(FrappeUI);
	app.use(pageMetaPlugin);

	const socket = initSocket();
	app.config.globalProperties.$socket = socket;

	app.mount("#app");
}

bootstrap();
