/** @type {import('tailwindcss').Config} */

import tailwindConfig from "frappe-ui/tailwind";

export default {
	presets: [tailwindConfig],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			colors: {
				primary: "#2c7677",
				"primary-dark": "#236061",
				"background-light": "#f0f2f4",
				"background-dark": "#19202e",
				"surface-light": "#ffffff",
				"surface-dark": "#1f293a",
			},
			fontFamily: {
				display: ["Manrope", "sans-serif"],
			},
			borderRadius: {
				DEFAULT: "0.5rem",
				lg: "1rem",
				xl: "1.5rem",
				full: "9999px",
			},
		},
	},
	plugins: [],
};
