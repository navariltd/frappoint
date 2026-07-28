import { reactive } from "vue";
import { getBookingDeskBranding } from "@/api/branding.api";
import fallbackLogo from "@/assets/images/Enashipai_logo.jpg";

const DEFAULTS = Object.freeze({
	company: "Enashipai Resort & Spa",
	pageTitle: "Enashipai Booking Desk",
	sidebarLogo: fallbackLogo,
	favicon: "/favicon.ico",
	primaryColor: "#8a0e04",
	primaryHoverColor: "#6f0a02",
	accentColor: "#a06f22",
	lightSurfaceColor: "#feffff",
	pageBackgroundColor: "#f8f4ee",
	bodyTextColor: "#2d2d2d",
});

const COLOR_FIELDS = {
	primaryColor: "primary_color",
	primaryHoverColor: "primary_hover_color",
	accentColor: "accent_color",
	lightSurfaceColor: "light_surface_color",
	pageBackgroundColor: "page_background_color",
	bodyTextColor: "body_text_color",
};

export const branding = reactive({ ...DEFAULTS });

function normalizeHex(value, fallback) {
	const color = String(value || "").trim();
	if (/^#[0-9a-f]{6}$/i.test(color)) {
		return color.toLowerCase();
	}
	if (/^#[0-9a-f]{3}$/i.test(color)) {
		return `#${color
			.slice(1)
			.split("")
			.map((character) => character.repeat(2))
			.join("")}`.toLowerCase();
	}
	return fallback;
}

function toRgb(hex) {
	const normalized = normalizeHex(hex, "#000000").slice(1);
	return [
		Number.parseInt(normalized.slice(0, 2), 16),
		Number.parseInt(normalized.slice(2, 4), 16),
		Number.parseInt(normalized.slice(4, 6), 16),
	];
}

function mix(first, second, secondWeight) {
	const start = toRgb(first);
	const end = toRgb(second);
	const weight = Math.min(1, Math.max(0, secondWeight));
	return start.map((channel, index) => Math.round(channel * (1 - weight) + end[index] * weight));
}

function luminance(rgb) {
	const [red, green, blue] = rgb.map((channel) => {
		const value = channel / 255;
		return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(first, second) {
	const lighter = Math.max(luminance(first), luminance(second));
	const darker = Math.min(luminance(first), luminance(second));
	return (lighter + 0.05) / (darker + 0.05);
}

function readableForeground(background, preferred, minimum = 4.5) {
	const backgroundRgb = Array.isArray(background) ? background : toRgb(background);
	const preferredRgb = Array.isArray(preferred) ? preferred : toRgb(preferred);
	if (contrast(backgroundRgb, preferredRgb) >= minimum) {
		return preferredRgb;
	}

	const dark = [0, 0, 0];
	const light = [255, 255, 255];
	return contrast(backgroundRgb, dark) >= contrast(backgroundRgb, light) ? dark : light;
}

function accessibleAccentText(accent, surface) {
	const accentRgb = toRgb(accent);
	const surfaceRgb = toRgb(surface);
	if (contrast(accentRgb, surfaceRgb) >= 4.5) {
		return accentRgb;
	}

	for (let weight = 0.1; weight <= 0.8; weight += 0.05) {
		const candidate = mix(accent, "#000000", weight);
		if (contrast(candidate, surfaceRgb) >= 4.5) {
			return candidate;
		}
	}
	return [45, 45, 45];
}

function rgbValue(value) {
	const rgb = Array.isArray(value) ? value : toRgb(value);
	return rgb.join(" ");
}

function createThemeTokens(settings) {
	const primary = settings.primaryColor;
	const primaryHover = settings.primaryHoverColor;
	const accent = settings.accentColor;
	const surface = settings.lightSurfaceColor;
	const background = settings.pageBackgroundColor;
	const configuredText = settings.bodyTextColor;
	const bodyText = readableForeground(background, configuredText);
	const surfaceText = readableForeground(surface, configuredText);
	const primaryContainer = mix(primary, surface, 0.84);
	const accentContainer = mix(accent, surface, 0.84);
	const surfaceLow = mix(background, surface, 0.35);
	const surfaceContainer = mix(background, surface, 0.58);
	const surfaceHigh = mix(background, accent, 0.1);
	const surfaceHighest = mix(background, accent, 0.17);
	const outline = mix(surfaceText, surface, 0.38);
	const outlineVariant = mix(surfaceText, surface, 0.75);
	const accentInk = accessibleAccentText(accent, surface);

	return {
		primary,
		"primary-dark": primaryHover,
		"on-primary": readableForeground(primary, "#ffffff"),
		"primary-container": primaryContainer,
		"on-primary-container": readableForeground(primaryContainer, primaryHover),
		"primary-fixed": primaryContainer,
		"primary-fixed-dim": mix(primary, surface, 0.7),
		"on-primary-fixed": readableForeground(primaryContainer, primaryHover),
		"on-primary-fixed-variant": readableForeground(primaryContainer, primary),
		"inverse-primary": mix(primary, "#ffffff", 0.58),
		"surface-tint": primary,

		secondary: accent,
		"secondary-dark": mix(accent, "#000000", 0.24),
		"secondary-ink": accentInk,
		"on-secondary": readableForeground(accent, configuredText),
		"secondary-container": accentContainer,
		"on-secondary-container": readableForeground(accentContainer, accentInk),
		"secondary-fixed": accentContainer,
		"secondary-fixed-dim": mix(accent, surface, 0.68),
		"on-secondary-fixed": readableForeground(accentContainer, accentInk),
		"on-secondary-fixed-variant": readableForeground(accentContainer, accentInk),

		tertiary: surface,
		"on-tertiary": surfaceText,
		"tertiary-container": accentContainer,
		"on-tertiary-container": readableForeground(accentContainer, accentInk),
		"tertiary-fixed": mix(accent, surface, 0.9),
		"tertiary-fixed-dim": mix(accent, surface, 0.72),
		"on-tertiary-fixed": readableForeground(accentContainer, accentInk),
		"on-tertiary-fixed-variant": readableForeground(accentContainer, accentInk),

		background,
		"background-light": background,
		"background-dark": mix(bodyText, "#000000", 0.28),
		"on-background": bodyText,
		surface: surfaceLow,
		"surface-light": surface,
		"surface-dark": mix(surfaceText, "#000000", 0.3),
		"surface-bright": surface,
		"surface-dim": mix(background, surfaceText, 0.12),
		"surface-container-lowest": surface,
		"surface-container-low": surfaceLow,
		"surface-container": surfaceContainer,
		"surface-container-high": surfaceHigh,
		"surface-container-highest": surfaceHighest,
		"surface-variant": surfaceContainer,
		"on-surface": surfaceText,
		"on-surface-variant": mix(surfaceText, surface, 0.22),
		"inverse-surface": mix(surfaceText, "#000000", 0.18),
		"inverse-on-surface": readableForeground(mix(surfaceText, "#000000", 0.18), "#ffffff"),

		outline,
		"outline-variant": outlineVariant,
		"border-light": mix(surfaceText, surface, 0.82),
		"border-dark": mix(surfaceText, "#000000", 0.15),
		"text-main-light": surfaceText,
		"text-main-dark": readableForeground(surfaceText, "#ffffff"),
		"text-sub-light": mix(surfaceText, surface, 0.22),
		"text-sub-dark": mix(surface, surfaceText, 0.2),
	};
}

function applyTheme(settings) {
	const root = document.documentElement;
	for (const [token, value] of Object.entries(createThemeTokens(settings))) {
		root.style.setProperty(`--color-${token}`, rgbValue(value));
	}
}

function applyDocumentBranding(settings) {
	document.title = settings.pageTitle;

	let themeColor = document.querySelector("meta[name='theme-color']");
	if (!themeColor) {
		themeColor = document.createElement("meta");
		themeColor.name = "theme-color";
		document.head.appendChild(themeColor);
	}
	themeColor.content = settings.primaryColor;

	let favicon = document.querySelector("link[rel~='icon']");
	if (!favicon) {
		favicon = document.createElement("link");
		favicon.rel = "icon";
		document.head.appendChild(favicon);
	}
	favicon.href = settings.favicon;
}

function mapSettings(response = {}) {
	const mapped = {
		company: response.company || DEFAULTS.company,
		pageTitle: response.page_title || DEFAULTS.pageTitle,
		sidebarLogo: response.sidebar_logo || DEFAULTS.sidebarLogo,
		favicon: response.favicon || DEFAULTS.favicon,
	};

	for (const [frontendField, backendField] of Object.entries(COLOR_FIELDS)) {
		mapped[frontendField] = normalizeHex(response[backendField], DEFAULTS[frontendField]);
	}
	return mapped;
}

export async function initializeBranding() {
	let settings = { ...DEFAULTS };
	try {
		settings = mapSettings(await getBookingDeskBranding());
	} catch {
		// The bundled theme remains usable when settings cannot be loaded.
	}

	Object.assign(branding, settings);
	applyTheme(settings);
	applyDocumentBranding(settings);
	return branding;
}
