import { createApp } from "vue";
import App from "./App.vue";
import { initSocket } from "./socket";

import { frappeRequest, FrappeUI, pageMetaPlugin, setConfig } from "frappe-ui";
import "./index.css";

setConfig("resourceFetcher", frappeRequest);

const app = createApp(App);

app.use(FrappeUI);
app.use(pageMetaPlugin);

const socket = initSocket();
app.config.globalProperties.$socket = socket;

app.mount("#booking-desk");
