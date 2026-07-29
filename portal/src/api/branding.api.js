import { createResource } from "frappe-ui";

const brandingResource = createResource({
	url: "frappoint.frappoint.api.branding.get_booking_desk_branding",
	auto: false,
});

export async function getPortalBranding() {
	const response = await brandingResource.fetch();
	const payload = response ?? brandingResource.data;
	return payload?.message ?? payload ?? {};
}
