import { defineStore } from "pinia";
import { fetchServiceDetails } from "@/api/serviceDetails.api";

function normalizeListField(value) {
	if (Array.isArray(value)) {
		return value
			.map((item) => {
				if (typeof item === "string") {
					return item.trim();
				}

				if (item && typeof item === "object") {
					return (
						item.label ||
						item.name ||
						item.title ||
						item.value ||
						item.description ||
						""
					).trim();
				}

				return "";
			})
			.filter(Boolean);
	}

	if (typeof value === "string") {
		if (/<(ul|ol|li|p|br)\b/i.test(value)) {
			const parser = new DOMParser();
			const document = parser.parseFromString(`<div>${value}</div>`, "text/html");
			const listItems = Array.from(document.querySelectorAll("li"))
				.map((item) => item.textContent?.trim() || "")
				.filter(Boolean);

			if (listItems.length) {
				return listItems;
			}

			const paragraphs = Array.from(document.querySelectorAll("p"))
				.map((item) => item.textContent?.trim() || "")
				.filter(Boolean);

			if (paragraphs.length) {
				return paragraphs;
			}

			const text = document.body.textContent || "";
			return text
				.split(/\r?\n/)
				.map((item) => item.trim())
				.filter(Boolean);
		}

		return value
			.split(/\r?\n|,/)
			.map((item) => item.trim())
			.filter(Boolean);
	}

	return [];
}

export const useServiceDetailsStore = defineStore("service-details", {
	state: () => ({
		serviceDetails: null,
		loading: false,
		error: "",
		selectedPackageKey: "",
		currentServiceType: "",
		requestId: 0,
	}),

	getters: {
		packages(state) {
			return state.serviceDetails?.prices || [];
		},

		selectedPackage(state) {
			const packages = state.serviceDetails?.prices || [];
			if (!packages.length) {
				return null;
			}

			return (
				packages.find((price) => price.price_name === state.selectedPackageKey) || packages[0]
			);
		},

		formattedBenefits(state) {
			return normalizeListField(state.serviceDetails?.benefits);
		},

		formattedTechniques(state) {
			return normalizeListField(state.serviceDetails?.techniques);
		},
	},

	actions: {
		clearServiceDetails() {
			this.serviceDetails = null;
			this.loading = false;
			this.error = "";
			this.selectedPackageKey = "";
			this.currentServiceType = "";
		},

		setSelectedPackage(packageOrKey) {
			if (!packageOrKey) {
				this.selectedPackageKey = "";
				return;
			}

			if (typeof packageOrKey === "string") {
				this.selectedPackageKey = packageOrKey;
				return;
			}

			this.selectedPackageKey = packageOrKey.price_name || packageOrKey.name || "";
		},

		async fetchServiceDetails(serviceType) {
			if (!serviceType) {
				this.clearServiceDetails();
				return null;
			}

			const nextRequestId = this.requestId + 1;
			this.requestId = nextRequestId;
			this.loading = true;
			this.error = "";
			this.currentServiceType = serviceType;
			this.serviceDetails = null;
			this.selectedPackageKey = "";

			try {
				const service = await fetchServiceDetails(serviceType);

				if (this.requestId !== nextRequestId) {
					return service;
				}

				this.serviceDetails = service;
				const defaultPackage =
					service?.prices?.find(
						(price) =>
							Number(price.duration) ===
							Number(service.default_duration_in_minutes)
					) || service?.prices?.[0];
				this.selectedPackageKey =
					defaultPackage?.price_name || defaultPackage?.name || "";
				return service;
			} catch (error) {
				if (this.requestId !== nextRequestId) {
					return null;
				}

				this.serviceDetails = null;
				this.selectedPackageKey = "";
				this.error = error?.message || "Unable to load service details.";
				return null;
			} finally {
				if (this.requestId === nextRequestId) {
					this.loading = false;
				}
			}
		},
	},
});
