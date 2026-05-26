import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				outDir: "../frappoint/public/booking_desk",
				indexHtmlPath: "../frappoint/www/booking_desk/index.html",
				emptyOutDir: true,
				sourcemap: true,
			},
		}),
		vue(),
	],
	build: {
		chunkSizeWarningLimit: 1500,
		outDir: "../frappoint/public/booking_desk",
		emptyOutDir: true,
		target: "es2015",
		sourcemap: true,
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
		exclude: ["frappe-ui"],
	},
	server: {
		allowedHosts: true,
	},
});
