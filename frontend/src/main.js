import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import { initSocket } from "./socket";
import { createPinia } from "pinia";

import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	Input,
	TextInput,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin,
	setConfig,
} from "frappe-ui";

import "./index.css";

const globalComponents = {
	Button,
	TextInput,
	Input,
	FormControl,
	ErrorMessage,
	Dialog,
	Alert,
	Badge,
};

const pinia = createPinia();

const app = createApp(App);

setConfig("resourceFetcher", frappeRequest);

app.use(router);
app.use(pinia);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

const socket = initSocket();
app.config.globalProperties.$socket = socket;

for (const key in globalComponents) {
	app.component(key, globalComponents[key]);
}

app.mount("#app");
