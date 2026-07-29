/** @type {import('tailwindcss').Config} */

import tailwindConfig from "frappe-ui/tailwind";

const themeColor = (name) => `rgb(var(--color-${name}) / <alpha-value>)`;

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
				primary: themeColor("primary"),
				"primary-dark": themeColor("primary-dark"),
				"on-primary": themeColor("on-primary"),
				"primary-container": themeColor("primary-container"),
				"on-primary-container": themeColor("on-primary-container"),
				"primary-fixed": themeColor("primary-fixed"),
				"primary-fixed-dim": themeColor("primary-fixed-dim"),
				"on-primary-fixed": themeColor("on-primary-fixed"),
				"on-primary-fixed-variant": themeColor("on-primary-fixed-variant"),
				"inverse-primary": themeColor("inverse-primary"),
				"surface-tint": themeColor("surface-tint"),

				secondary: themeColor("secondary"),
				"secondary-dark": themeColor("secondary-dark"),
				"secondary-ink": themeColor("secondary-ink"),
				"on-secondary": themeColor("on-secondary"),
				"secondary-container": themeColor("secondary-container"),
				"on-secondary-container": themeColor("on-secondary-container"),
				"secondary-fixed": themeColor("secondary-fixed"),
				"secondary-fixed-dim": themeColor("secondary-fixed-dim"),
				"on-secondary-fixed": themeColor("on-secondary-fixed"),
				"on-secondary-fixed-variant": themeColor("on-secondary-fixed-variant"),

				tertiary: themeColor("tertiary"),
				"on-tertiary": themeColor("on-tertiary"),
				"tertiary-container": themeColor("tertiary-container"),
				"on-tertiary-container": themeColor("on-tertiary-container"),
				"tertiary-fixed": themeColor("tertiary-fixed"),
				"tertiary-fixed-dim": themeColor("tertiary-fixed-dim"),
				"on-tertiary-fixed": themeColor("on-tertiary-fixed"),
				"on-tertiary-fixed-variant": themeColor("on-tertiary-fixed-variant"),

				background: themeColor("background"),
				"background-light": themeColor("background-light"),
				"background-dark": themeColor("background-dark"),
				"on-background": themeColor("on-background"),
				surface: themeColor("surface"),
				"surface-light": themeColor("surface-light"),
				"surface-dark": themeColor("surface-dark"),
				"surface-bright": themeColor("surface-bright"),
				"surface-dim": themeColor("surface-dim"),
				"surface-container-lowest": themeColor("surface-container-lowest"),
				"surface-container-low": themeColor("surface-container-low"),
				"surface-container": themeColor("surface-container"),
				"surface-container-high": themeColor("surface-container-high"),
				"surface-container-highest": themeColor("surface-container-highest"),
				"surface-variant": themeColor("surface-variant"),
				"on-surface": themeColor("on-surface"),
				"on-surface-variant": themeColor("on-surface-variant"),
				"inverse-surface": themeColor("inverse-surface"),
				"inverse-on-surface": themeColor("inverse-on-surface"),

				outline: themeColor("outline"),
				"outline-variant": themeColor("outline-variant"),
				"border-light": themeColor("border-light"),
				"border-dark": themeColor("border-dark"),
				"text-main-light": themeColor("text-main-light"),
				"text-main-dark": themeColor("text-main-dark"),
				"text-sub-light": themeColor("text-sub-light"),
				"text-sub-dark": themeColor("text-sub-dark"),

				success: "#256c3a",
				warning: "#8a5b12",
				error: "#a31818",
				"on-error": "#ffffff",
				"error-container": "#f9dedd",
				"on-error-container": "#7c1111",
			},
			borderRadius: {
				DEFAULT: "0.25rem",
				lg: "0.5rem",
				xl: "0.75rem",
				full: "9999px",
			},
			spacing: {
				gutter: "16px",
				base: "8px",
				"section-gap": "48px",
				"stack-sm": "12px",
				"container-padding": "24px",
				"stack-md": "24px",
			},
			fontFamily: {
				"headline-lg": ["Outfit"],
				"body-md": ["Inter"],
				"body-lg": ["Inter"],
				"label-sm": ["Inter"],
				"label-md": ["Inter"],
				"headline-md": ["Outfit"],
				"headline-sm": ["Outfit"],
			},
			fontSize: {
				"headline-lg": [
					"40px",
					{ lineHeight: "48px", letterSpacing: "-0.02em", fontWeight: "600" },
				],
				"body-md": [
					"16px",
					{ lineHeight: "24px", letterSpacing: "0.01em", fontWeight: "400" },
				],
				"body-lg": [
					"18px",
					{ lineHeight: "28px", letterSpacing: "0.01em", fontWeight: "400" },
				],
				"label-sm": [
					"12px",
					{ lineHeight: "16px", letterSpacing: "0.03em", fontWeight: "500" },
				],
				"label-md": [
					"14px",
					{ lineHeight: "20px", letterSpacing: "0.05em", fontWeight: "600" },
				],
				"headline-md": [
					"28px",
					{ lineHeight: "36px", letterSpacing: "-0.01em", fontWeight: "500" },
				],
				"headline-sm": [
					"20px",
					{ lineHeight: "28px", letterSpacing: "0em", fontWeight: "500" },
				],
			},
		},
	},
	plugins: [],
};
