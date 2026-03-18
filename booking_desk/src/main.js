import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { initSocket } from "./socket";
import { createPinia } from "pinia";

import { frappeRequest, FrappeUI, pageMetaPlugin, setConfig } from "frappe-ui";
import "./index.css";

setConfig("resourceFetcher", frappeRequest);

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(FrappeUI);
app.use(pageMetaPlugin);

const socket = initSocket();
app.config.globalProperties.$socket = socket;

app.mount("#app");
