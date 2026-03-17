import path from "node:path";

import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				outDir: "../frappoint/public/booking_desk",
				indexHtmlPath: "../frappoint/public/booking_desk/index.html",
				emptyOutDir: true,
				sourcemap: true,
				rollupOptions: {
					output: {
						entryFileNames: "vue-booking-desk.js",
						chunkFileNames: "vue-booking-desk-[name].js",
						assetFileNames: "vue-booking-desk-[name].[ext]",
					},
				},
			},
		}),
		vue(),
		vueDevTools(),
	],
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
			"@": path.resolve(__dirname, "src"),
			"tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
		},
	},
	optimizeDeps: {
		include: [
			"frappe-ui > feather-icons",
			"tailwind.config.js",
			"interactjs",
			"showdown",
			"highlight.js/lib/core",
			"engine.io-client",
		],
	},
	server: {
		allowedHosts: true,
	},
});
