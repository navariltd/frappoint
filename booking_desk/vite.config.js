import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";

// https://vite.dev/config/
export default defineConfig({
	plugins: [vue(), vueDevTools()],
	build: {
		chunkSizeWarningLimit: 1500,
		outDir: "../frappoint/public/booking_desk",
		filenameHashing: false,
		emptyOutDir: true,
		target: "es2015",
		sourcemap: true,
		rollupOptions: {
			output: {
				entryFileNames: "vue-booking-desk.js",
				chunkFileNames: "vue-booking-desk-[name].js",
				assetFileNames: "vue-booking-desk-[name].[ext]",
			},
		},
	},
	resolve: {
		alias: {
			"@": fileURLToPath(new URL("./src", import.meta.url)),
		},
	},
});
