/**
 * Transforms slot availability API response into flat list of individual slots by provider
 *
 * @param {Array} response - API response with structure: [{ date, slots: [{ start_time, end_time, providers: [...] }] }]
 * @returns {Array} Flattened array of individual slot offerings
 */
export function flattenSlotsByProvider(response) {
	if (!response || !Array.isArray(response)) return [];

	return response.flatMap((dateGroup) =>
		(dateGroup.slots || []).flatMap((slot) =>
			(slot.providers || []).map((provider) => ({
				start_time: slot.start_time,
				end_time: slot.end_time,
				duration: slot.duration,
				buffer_before: slot.buffer_before,
				buffer_after: slot.buffer_after,
				provider: provider.provider,
				provider_name: provider.provider_name,
				service_unit: provider.service_unit,
				service_unit_name: provider.service_unit_name,
				slot_ids: provider.slot_ids,
				shift_assignment: provider.shift_assignment,
			}))
		)
	);
}

/**
 * Extracts and flattens slots for a specific date from API response
 *
 * @param {Array} response - Full API response
 * @param {string} date - Target date to filter (YYYY-MM-DD format)
 * @returns {Array} Flattened slots for the specified date
 */
export function flattenSlotsByProviderForDate(response, date) {
	if (!response || !Array.isArray(response)) return [];

	const dateGroup = response.find((group) => group.date === date);

	if (!dateGroup || !dateGroup.slots) {
		return [];
	}

	return dateGroup.slots.flatMap((slot) =>
		(slot.providers || []).map((provider) => ({
			start_time: slot.start_time,
			end_time: slot.end_time,
			duration: slot.duration,
			buffer_before: slot.buffer_before,
			buffer_after: slot.buffer_after,
			provider: provider.provider,
			provider_name: provider.provider_name,
			service_unit: provider.service_unit,
			service_unit_name: provider.service_unit_name,
			slot_ids: provider.slot_ids,
			shift_assignment: provider.shift_assignment,
		}))
	);
}
