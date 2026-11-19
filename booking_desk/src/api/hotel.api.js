import { createResource } from "frappe-ui";
import { readableError } from "@/utils/errorMessage";

const HOSPITALITY_API = "frappoint.vuna_hospitality.api";

export const HOTEL_ENDPOINTS = {
	sessionContext: `${HOSPITALITY_API}.session.get_session_context`,
	deskContext: `${HOSPITALITY_API}.reservations.get_booking_desk_context`,
	searchAvailability: `${HOSPITALITY_API}.quote.search_availability`,
	searchGuests: `${HOSPITALITY_API}.guests.search_guests`,
	createGuest: `${HOSPITALITY_API}.guests.create_guest`,
	holdStays: `${HOSPITALITY_API}.reservations.hold_stays`,
	confirmStay: `${HOSPITALITY_API}.reservations.confirm_stay`,
	confirmBooking: `${HOSPITALITY_API}.reservations.confirm_booking`,
	cancelStay: `${HOSPITALITY_API}.reservations.cancel_stay`,
	cancelBooking: `${HOSPITALITY_API}.reservations.cancel_booking`,
	getBooking: `${HOSPITALITY_API}.reservations.get_booking`,
	recentBookings: `${HOSPITALITY_API}.reservations.get_recent_bookings`,
	frontDeskToday: `${HOSPITALITY_API}.front_desk.get_front_desk_today`,
	stay: `${HOSPITALITY_API}.front_desk.get_stay`,
	assignableRooms: `${HOSPITALITY_API}.front_desk.get_assignable_rooms`,
	moveReasons: `${HOSPITALITY_API}.front_desk.get_move_reasons`,
	assignRoom: `${HOSPITALITY_API}.front_desk.assign_room`,
	unassignRoom: `${HOSPITALITY_API}.front_desk.unassign_room`,
	setRoomLock: `${HOSPITALITY_API}.front_desk.set_room_lock`,
	moveRoom: `${HOSPITALITY_API}.front_desk.move_room`,
	checkIn: `${HOSPITALITY_API}.front_desk.check_in`,
	checkOut: `${HOSPITALITY_API}.front_desk.check_out`,
	addStayGuest: `${HOSPITALITY_API}.front_desk.add_stay_guest`,
	removeStayGuest: `${HOSPITALITY_API}.front_desk.remove_stay_guest`,
	setPrimaryGuest: `${HOSPITALITY_API}.front_desk.set_primary_guest`,
	registerGuest: `${HOSPITALITY_API}.front_desk.register_guest`,
	checkInGuest: `${HOSPITALITY_API}.front_desk.check_in_guest`,
	stayFolios: `${HOSPITALITY_API}.folios.get_stay_folios`,
	searchFolioItems: `${HOSPITALITY_API}.folios.search_items`,
	folioItemRate: `${HOSPITALITY_API}.folios.get_item_rate`,
	postFolioCharge: `${HOSPITALITY_API}.folios.post_charge`,
	reverseFolioTransaction: `${HOSPITALITY_API}.folios.reverse_transaction`,
	rebuildFolioBalance: `${HOSPITALITY_API}.folios.rebuild_folio_balance`,
	addFolio: `${HOSPITALITY_API}.folios.add_folio`,
	setFolioPayee: `${HOSPITALITY_API}.folios.set_folio_payee`,
	transferCharge: `${HOSPITALITY_API}.folios.transfer_charge`,
	settleFolio: `${HOSPITALITY_API}.folios.settle_folio`,
	releaseSettlement: `${HOSPITALITY_API}.folios.release_settlement`,
	issueCreditNote: `${HOSPITALITY_API}.folios.issue_credit_note`,
	nightAudit: `${HOSPITALITY_API}.night_audit.get_night_audit`,
	startNightAudit: `${HOSPITALITY_API}.night_audit.start_night_audit`,
	cashier: `${HOSPITALITY_API}.cashiering.get_cashier`,
	openShift: `${HOSPITALITY_API}.cashiering.open_shift`,
	closeShift: `${HOSPITALITY_API}.cashiering.close_shift`,
	reviewShift: `${HOSPITALITY_API}.cashiering.review_shift`,
	takePayment: `${HOSPITALITY_API}.cashiering.take_payment`,
	payment: `${HOSPITALITY_API}.cashiering.get_payment`,
	cancelPayment: `${HOSPITALITY_API}.cashiering.cancel_payment`,
	refundPayment: `${HOSPITALITY_API}.cashiering.refund_payment`,
	reinstateStay: `${HOSPITALITY_API}.reservations.reinstate_stay`,
	departEarly: `${HOSPITALITY_API}.front_desk.depart_early`,
	takeDeposit: `${HOSPITALITY_API}.deposits.take_deposit`,
	waiveDeposit: `${HOSPITALITY_API}.deposits.waive_deposit`,
	addRoutingRule: `${HOSPITALITY_API}.folios.add_routing_rule`,
	removeRoutingRule: `${HOSPITALITY_API}.folios.remove_routing_rule`,
	houseAccounts: `${HOSPITALITY_API}.folios.get_house_accounts`,
	createHouseAccount: `${HOSPITALITY_API}.folios.create_house_account`,
	houseAccountFolios: `${HOSPITALITY_API}.folios.get_house_account_folios`,
	openHouseAccountFolio: `${HOSPITALITY_API}.folios.open_house_account_folio`,
	closeHouseAccount: `${HOSPITALITY_API}.folios.close_house_account`,
	rateGrid: `${HOSPITALITY_API}.rates.get_rate_grid`,
	setRates: `${HOSPITALITY_API}.rates.set_rates`,
	resetRates: `${HOSPITALITY_API}.rates.reset_rates`,
	regenerateRates: `${HOSPITALITY_API}.rates.regenerate_rates`,
	setRestrictions: `${HOSPITALITY_API}.rates.set_restrictions`,
	previewDepartureChange: `${HOSPITALITY_API}.front_desk.preview_departure_change`,
	changeDeparture: `${HOSPITALITY_API}.front_desk.change_departure`,
	housekeepingBoard: `${HOSPITALITY_API}.housekeeping.get_housekeeping_board`,
	planStayovers: `${HOSPITALITY_API}.housekeeping.plan_stayovers`,
	createHousekeepingTask: `${HOSPITALITY_API}.housekeeping.create_task`,
	assignHousekeepingTask: `${HOSPITALITY_API}.housekeeping.assign_task`,
	startHousekeepingTask: `${HOSPITALITY_API}.housekeeping.start_task`,
	finishHousekeepingTask: `${HOSPITALITY_API}.housekeeping.finish_task`,
	markDoNotDisturb: `${HOSPITALITY_API}.housekeeping.mark_do_not_disturb`,
	inspectHousekeepingTask: `${HOSPITALITY_API}.housekeeping.inspect_task`,
	cancelHousekeepingTask: `${HOSPITALITY_API}.housekeeping.cancel_task`,
	reportMaintenance: `${HOSPITALITY_API}.housekeeping.report_maintenance`,
	approveMaintenance: `${HOSPITALITY_API}.housekeeping.approve_maintenance`,
	startMaintenance: `${HOSPITALITY_API}.housekeeping.start_maintenance`,
	resolveMaintenance: `${HOSPITALITY_API}.housekeeping.resolve_maintenance`,
	cancelMaintenance: `${HOSPITALITY_API}.housekeeping.cancel_maintenance`,
	searchServiceStays: `${HOSPITALITY_API}.services.search_stays`,
	chargeBookingToRoom: `${HOSPITALITY_API}.services.charge_booking_to_room`,
	releaseBookingToDesk: `${HOSPITALITY_API}.services.release_booking_to_desk`,
	retryServicePosting: `${HOSPITALITY_API}.services.retry_service_posting`,
	waiveServiceFee: `${HOSPITALITY_API}.services.waive_service_fee`,
	rankedRooms: `${HOSPITALITY_API}.front_desk.get_ranked_rooms`,
	guestInsights: `${HOSPITALITY_API}.preferences.get_guest_insights`,
	preferenceOptions: `${HOSPITALITY_API}.preferences.get_preference_options`,
	addGuestPreference: `${HOSPITALITY_API}.preferences.add_guest_preference`,
	retireGuestPreference: `${HOSPITALITY_API}.preferences.retire_guest_preference`,
	addStayRequest: `${HOSPITALITY_API}.preferences.add_stay_request`,
	closeStayRequest: `${HOSPITALITY_API}.preferences.close_stay_request`,
	copyRequestToProfile: `${HOSPITALITY_API}.preferences.copy_request_to_profile`,
	applySuggestion: `${HOSPITALITY_API}.preferences.apply_suggestion`,
	saveSuggestion: `${HOSPITALITY_API}.preferences.save_suggestion`,
	dismissSuggestion: `${HOSPITALITY_API}.preferences.dismiss_suggestion`,
	historyMatches: `${HOSPITALITY_API}.preferences.get_history_matches`,
	findHistoryMatches: `${HOSPITALITY_API}.preferences.find_history_matches`,
	reviewHistoryMatch: `${HOSPITALITY_API}.preferences.review_history_match`,
};

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

async function request(url, params = {}) {
	const resource = createResource({ url, auto: false });
	const response = await resource.fetch(params);
	return unwrapPayload(response ?? resource.data);
}

/** The server's message for a failed call, without the traceback. */
// Plain words for the desk: no markup, no internal names (see utils/errorMessage.js).
export function hotelErrorMessage(error) {
	return readableError(error);
}

export const fetchSessionContextApi = () => request(HOTEL_ENDPOINTS.sessionContext);
export const fetchDeskContextApi = () => request(HOTEL_ENDPOINTS.deskContext);

export const searchAvailabilityApi = ({
	property,
	arrival,
	departure,
	adults,
	children,
	childAges = [],
}) =>
	request(HOTEL_ENDPOINTS.searchAvailability, {
		property,
		arrival,
		departure,
		adults,
		children,
		child_ages: JSON.stringify(childAges),
	});

export const searchGuestsApi = (text) => request(HOTEL_ENDPOINTS.searchGuests, { text });

export const createGuestApi = (guest) => request(HOTEL_ENDPOINTS.createGuest, guest);

export const holdStaysApi = ({ property, stays, booking, bookingDetails }) =>
	request(HOTEL_ENDPOINTS.holdStays, {
		property,
		stays,
		booking: booking || null,
		booking_details: bookingDetails || {},
	});

export const confirmStayApi = (stay) => request(HOTEL_ENDPOINTS.confirmStay, { stay });
export const confirmBookingApi = (booking) => request(HOTEL_ENDPOINTS.confirmBooking, { booking });
export const cancelStayApi = (stay, reason, { waiveFee = false, waiveReason = null } = {}) =>
	request(HOTEL_ENDPOINTS.cancelStay, {
		stay,
		reason,
		waive_fee: waiveFee ? 1 : 0,
		waive_reason: waiveReason,
	});
export const reinstateStayApi = (stay, reason) =>
	request(HOTEL_ENDPOINTS.reinstateStay, { stay, reason });
export const cancelBookingApi = (booking, reason) =>
	request(HOTEL_ENDPOINTS.cancelBooking, { booking, reason });
export const fetchBookingApi = (booking) => request(HOTEL_ENDPOINTS.getBooking, { booking });
export const fetchRecentBookingsApi = (property, limit = 20) =>
	request(HOTEL_ENDPOINTS.recentBookings, { property, limit });

// Front desk (F6)
export const fetchFrontDeskTodayApi = (property) =>
	request(HOTEL_ENDPOINTS.frontDeskToday, { property });
export const fetchStayApi = (stay) => request(HOTEL_ENDPOINTS.stay, { stay });
export const fetchAssignableRoomsApi = (stay) =>
	request(HOTEL_ENDPOINTS.assignableRooms, { stay });
export const fetchMoveReasonsApi = () => request(HOTEL_ENDPOINTS.moveReasons);
export const assignRoomApi = (stay, room, lock = false, preferenceOverrideReason = null) =>
	request(HOTEL_ENDPOINTS.assignRoom, {
		stay,
		room,
		lock: lock ? 1 : 0,
		preference_override_reason: preferenceOverrideReason || null,
	});
export const unassignRoomApi = (stay, reason) =>
	request(HOTEL_ENDPOINTS.unassignRoom, { stay, reason });
export const setRoomLockApi = (stay, locked, reason) =>
	request(HOTEL_ENDPOINTS.setRoomLock, { stay, locked: locked ? 1 : 0, reason });
export const moveRoomApi = (stay, room, moveReason, preferenceOverrideReason = null) =>
	request(HOTEL_ENDPOINTS.moveRoom, {
		stay,
		room,
		move_reason: moveReason,
		preference_override_reason: preferenceOverrideReason || null,
	});
export const checkInApi = (stay, room, overrideReason = null) =>
	request(HOTEL_ENDPOINTS.checkIn, {
		stay,
		room: room || null,
		override_reason: overrideReason || null,
	});
export const checkOutApi = (stay, overrideReason = null) =>
	request(HOTEL_ENDPOINTS.checkOut, { stay, override_reason: overrideReason });
export const departEarlyApi = (stay) => request(HOTEL_ENDPOINTS.departEarly, { stay });
export const addStayGuestApi = (stay, guestProfile, ageCategory = "Adult") =>
	request(HOTEL_ENDPOINTS.addStayGuest, {
		stay,
		guest_profile: guestProfile,
		age_category: ageCategory,
	});
export const removeStayGuestApi = (stayGuest, reason) =>
	request(HOTEL_ENDPOINTS.removeStayGuest, { stay_guest: stayGuest, reason });
export const setPrimaryGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.setPrimaryGuest, { stay_guest: stayGuest });
export const registerGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.registerGuest, { stay_guest: stayGuest });
export const checkInGuestApi = (stayGuest) =>
	request(HOTEL_ENDPOINTS.checkInGuest, { stay_guest: stayGuest });

// Folios (F7)
export const fetchStayFoliosApi = (stay) => request(HOTEL_ENDPOINTS.stayFolios, { stay });
export const searchFolioItemsApi = (folio, text) =>
	request(HOTEL_ENDPOINTS.searchFolioItems, { folio_name: folio, text });
export const fetchFolioItemRateApi = (folio, item) =>
	request(HOTEL_ENDPOINTS.folioItemRate, { folio_name: folio, item });
/** `requestId` stays the same across retries of one charge, so it posts once. */
export const postFolioChargeApi = ({
	folio,
	item,
	quantity,
	rate,
	description,
	stayGuest,
	notes,
	reason,
	requestId,
}) =>
	request(HOTEL_ENDPOINTS.postFolioCharge, {
		folio_name: folio,
		item,
		quantity,
		rate,
		description: description || null,
		stay_guest: stayGuest || null,
		notes: notes || null,
		reason: reason || null,
		request_id: requestId,
	});
export const reverseFolioTransactionApi = (transaction, reason) =>
	request(HOTEL_ENDPOINTS.reverseFolioTransaction, { transaction, reason });
export const rebuildFolioBalanceApi = (folio) =>
	request(HOTEL_ENDPOINTS.rebuildFolioBalance, { folio_name: folio });

// Several folios, transfers, settlement and credit notes (F11)
export const addFolioApi = ({ stay, label, payeeCustomer, payeeGuestProfile }) =>
	request(HOTEL_ENDPOINTS.addFolio, {
		stay,
		label: label || null,
		payee_customer: payeeCustomer || null,
		payee_guest_profile: payeeGuestProfile || null,
	});
export const setFolioPayeeApi = ({ folio, payeeCustomer, payeeGuestProfile }) =>
	request(HOTEL_ENDPOINTS.setFolioPayee, {
		folio_name: folio,
		payee_customer: payeeCustomer || null,
		payee_guest_profile: payeeGuestProfile || null,
	});
/** `requestId` stays the same across retries of one move, so the charge moves once. */
export const transferChargeApi = ({ transaction, toFolio, amount, reason, requestId }) =>
	request(HOTEL_ENDPOINTS.transferCharge, {
		transaction,
		to_folio: toFolio,
		amount: amount || null,
		reason: reason || null,
		request_id: requestId,
	});
export const settleFolioApi = (folio, { transferToAr = false, overrideReason = null } = {}) =>
	request(HOTEL_ENDPOINTS.settleFolio, {
		folio_name: folio,
		transfer_to_ar: transferToAr ? 1 : 0,
		override_reason: overrideReason,
	});
export const releaseSettlementApi = (folio, reason) =>
	request(HOTEL_ENDPOINTS.releaseSettlement, { folio_name: folio, reason });
export const issueCreditNoteApi = (transaction, reason) =>
	request(HOTEL_ENDPOINTS.issueCreditNote, { transaction, reason });

// Night audit (F8)
export const fetchNightAuditApi = (property) => request(HOTEL_ENDPOINTS.nightAudit, { property });
export const startNightAuditApi = (property) =>
	request(HOTEL_ENDPOINTS.startNightAudit, { property });

// Payments and cashier shifts (F10)
export const fetchCashierApi = (property) => request(HOTEL_ENDPOINTS.cashier, { property });
export const openShiftApi = (property, openingFloat, workstation) =>
	request(HOTEL_ENDPOINTS.openShift, {
		property,
		opening_float: openingFloat || 0,
		workstation: workstation || null,
	});
export const closeShiftApi = (shift, declared, reasons) =>
	request(HOTEL_ENDPOINTS.closeShift, {
		shift,
		declared: JSON.stringify(declared),
		reasons: JSON.stringify(reasons),
	});
export const reviewShiftApi = (shift, notes) =>
	request(HOTEL_ENDPOINTS.reviewShift, { shift, notes: notes || null });
/** `requestId` stays the same across retries of one payment, so it is taken once. */
export const takePaymentApi = ({
	property,
	splits,
	modeOfPayment,
	paymentGateway,
	phone,
	referenceNo,
	requestId,
}) =>
	request(HOTEL_ENDPOINTS.takePayment, {
		property,
		splits: JSON.stringify(splits),
		mode_of_payment: modeOfPayment || null,
		payment_gateway: paymentGateway || null,
		phone: phone || null,
		reference_no: referenceNo || null,
		request_id: requestId,
	});
export const fetchPaymentApi = (payment) => request(HOTEL_ENDPOINTS.payment, { payment });
export const cancelPaymentApi = (payment, reason) =>
	request(HOTEL_ENDPOINTS.cancelPayment, { payment, reason });
export const refundPaymentApi = (payment, amounts, reason) =>
	request(HOTEL_ENDPOINTS.refundPayment, { payment, amounts: JSON.stringify(amounts), reason });

// Deposits, routing and house accounts (F12)
/** `requestId` stays the same across retries of one deposit, so it is taken once. */
export const takeDepositApi = ({
	deposit,
	amount,
	modeOfPayment,
	paymentGateway,
	phone,
	referenceNo,
	requestId,
}) =>
	request(HOTEL_ENDPOINTS.takeDeposit, {
		deposit,
		amount: amount || null,
		mode_of_payment: modeOfPayment || null,
		payment_gateway: paymentGateway || null,
		phone: phone || null,
		reference_no: referenceNo || null,
		request_id: requestId,
	});
export const waiveDepositApi = (deposit, reason) =>
	request(HOTEL_ENDPOINTS.waiveDeposit, { deposit, reason });
export const addRoutingRuleApi = ({
	stay,
	targetFolio,
	route,
	chargeCode,
	itemGroup,
	stayGuest,
	notes,
}) =>
	request(HOTEL_ENDPOINTS.addRoutingRule, {
		stay,
		target_folio: targetFolio,
		route,
		charge_code: chargeCode || null,
		item_group: itemGroup || null,
		stay_guest: stayGuest || null,
		notes: notes || null,
	});
export const removeRoutingRuleApi = (rule, reason) =>
	request(HOTEL_ENDPOINTS.removeRoutingRule, { rule, reason });
export const fetchHouseAccountsApi = (property) =>
	request(HOTEL_ENDPOINTS.houseAccounts, { property });
export const createHouseAccountApi = ({
	property,
	accountName,
	accountType,
	payeeCustomer,
	validFrom,
	validTo,
	notes,
}) =>
	request(HOTEL_ENDPOINTS.createHouseAccount, {
		property,
		account_name: accountName,
		account_type: accountType || "Permanent",
		payee_customer: payeeCustomer || null,
		valid_from: validFrom || null,
		valid_to: validTo || null,
		notes: notes || null,
	});
export const fetchHouseAccountFoliosApi = (account) =>
	request(HOTEL_ENDPOINTS.houseAccountFolios, { account });
export const openHouseAccountFolioApi = (account) =>
	request(HOTEL_ENDPOINTS.openHouseAccountFolio, { account });
export const closeHouseAccountApi = (account, reason) =>
	request(HOTEL_ENDPOINTS.closeHouseAccount, { account, reason });

// Rates, restrictions and stay changes (F13)
export const fetchRateGridApi = ({ property, ratePlan, start, days }) =>
	request(HOTEL_ENDPOINTS.rateGrid, {
		property,
		rate_plan: ratePlan || null,
		start: start || null,
		days: days || 14,
	});
export const setRatesApi = ({
	ratePlan,
	roomTypes,
	fromDate,
	toDate,
	weekdays,
	rate,
	adjustPercent,
	adjustAmount,
	reason,
}) =>
	request(HOTEL_ENDPOINTS.setRates, {
		rate_plan: ratePlan,
		room_types: JSON.stringify(roomTypes),
		from_date: fromDate,
		to_date: toDate,
		weekdays: JSON.stringify(weekdays || []),
		rate: rate ?? null,
		adjust_percent: adjustPercent ?? null,
		adjust_amount: adjustAmount ?? null,
		reason: reason || null,
	});
export const resetRatesApi = ({ ratePlan, roomTypes, fromDate, toDate, weekdays }) =>
	request(HOTEL_ENDPOINTS.resetRates, {
		rate_plan: ratePlan,
		room_types: JSON.stringify(roomTypes),
		from_date: fromDate,
		to_date: toDate,
		weekdays: JSON.stringify(weekdays || []),
	});
export const regenerateRatesApi = (ratePlan) =>
	request(HOTEL_ENDPOINTS.regenerateRates, { rate_plan: ratePlan });
export const setRestrictionsApi = ({
	property,
	ratePlan,
	roomTypes,
	fromDate,
	toDate,
	weekdays,
	values,
	clear,
	notes,
}) =>
	request(HOTEL_ENDPOINTS.setRestrictions, {
		property,
		rate_plan: ratePlan || null,
		room_types: JSON.stringify(roomTypes || []),
		from_date: fromDate,
		to_date: toDate,
		weekdays: JSON.stringify(weekdays || []),
		values: JSON.stringify(values || {}),
		clear: clear ? 1 : 0,
		notes: notes || null,
	});
export const previewDepartureChangeApi = (stay, departure) =>
	request(HOTEL_ENDPOINTS.previewDepartureChange, { stay, departure });
export const changeDepartureApi = (stay, departure, overrideReason = null) =>
	request(HOTEL_ENDPOINTS.changeDeparture, {
		stay,
		departure,
		override_reason: overrideReason,
	});

// Services charged to a hotel stay
export const searchServiceStaysApi = (text) =>
	request(HOTEL_ENDPOINTS.searchServiceStays, { text: text || "" });
export const chargeBookingToRoomApi = ({ booking, stay, assignments, confirm = true }) =>
	request(HOTEL_ENDPOINTS.chargeBookingToRoom, {
		booking,
		stay,
		assignments: JSON.stringify(assignments),
		confirm: confirm ? 1 : 0,
	});
export const releaseBookingToDeskApi = (booking, reason) =>
	request(HOTEL_ENDPOINTS.releaseBookingToDesk, { booking, reason });
export const retryServicePostingApi = (appointment) =>
	request(HOTEL_ENDPOINTS.retryServicePosting, { appointment });
export const waiveServiceFeeApi = (participant, reason) =>
	request(HOTEL_ENDPOINTS.waiveServiceFee, { participant, reason });

// Housekeeping and maintenance
export const fetchHousekeepingBoardApi = (property) =>
	request(HOTEL_ENDPOINTS.housekeepingBoard, { property });
export const planStayoversApi = (property) => request(HOTEL_ENDPOINTS.planStayovers, { property });
export const createHousekeepingTaskApi = ({ room, taskType, priority, notes, assignedTo }) =>
	request(HOTEL_ENDPOINTS.createHousekeepingTask, {
		room,
		task_type: taskType,
		priority: priority || null,
		notes: notes || null,
		assigned_to: assignedTo || null,
	});
export const assignHousekeepingTaskApi = (task, employee) =>
	request(HOTEL_ENDPOINTS.assignHousekeepingTask, { task, employee: employee || null });
export const startHousekeepingTaskApi = (task) =>
	request(HOTEL_ENDPOINTS.startHousekeepingTask, { task });
export const finishHousekeepingTaskApi = (task, roomFound = null, notes = null) =>
	request(HOTEL_ENDPOINTS.finishHousekeepingTask, {
		task,
		room_found: roomFound || null,
		notes: notes || null,
	});
export const markDoNotDisturbApi = (task) => request(HOTEL_ENDPOINTS.markDoNotDisturb, { task });
export const inspectHousekeepingTaskApi = (task, passed, notes = null) =>
	request(HOTEL_ENDPOINTS.inspectHousekeepingTask, {
		task,
		passed: passed ? 1 : 0,
		notes: notes || null,
	});
export const cancelHousekeepingTaskApi = (task, reason) =>
	request(HOTEL_ENDPOINTS.cancelHousekeepingTask, { task, reason });
export const reportMaintenanceApi = ({
	property,
	issue,
	room,
	severity,
	description,
	roomImpact,
	outFrom,
	backInServiceOn,
}) =>
	request(HOTEL_ENDPOINTS.reportMaintenance, {
		property,
		issue,
		room: room || null,
		severity: severity || "Medium",
		description: description || null,
		room_impact: roomImpact || "None",
		out_from: outFrom || null,
		back_in_service_on: backInServiceOn || null,
	});
export const approveMaintenanceApi = (request_) =>
	request(HOTEL_ENDPOINTS.approveMaintenance, { request: request_ });
export const startMaintenanceApi = (request_) =>
	request(HOTEL_ENDPOINTS.startMaintenance, { request: request_ });
export const resolveMaintenanceApi = (request_, resolution) =>
	request(HOTEL_ENDPOINTS.resolveMaintenance, { request: request_, resolution });
export const cancelMaintenanceApi = (request_, reason) =>
	request(HOTEL_ENDPOINTS.cancelMaintenance, { request: request_, reason });

// Preferences, suggestions and ranked rooms (F18)
export const fetchRankedRoomsApi = (stay) => request(HOTEL_ENDPOINTS.rankedRooms, { stay });
export const fetchGuestInsightsApi = (stay, guestProfile = null) =>
	request(HOTEL_ENDPOINTS.guestInsights, { stay, guest_profile: guestProfile || null });
export const fetchPreferenceOptionsApi = () => request(HOTEL_ENDPOINTS.preferenceOptions);
export const addGuestPreferenceApi = (guestProfile, stay, fields) =>
	request(HOTEL_ENDPOINTS.addGuestPreference, {
		guest_profile: guestProfile,
		stay,
		category: fields.category,
		value: fields.value || null,
		priority: fields.priority,
		room_feature: fields.roomFeature || null,
		sensitive: fields.sensitive ? 1 : 0,
		this_property_only: fields.thisPropertyOnly ? 1 : 0,
	});
export const retireGuestPreferenceApi = (preference, stay, reason = null) =>
	request(HOTEL_ENDPOINTS.retireGuestPreference, { preference, stay, reason });
export const addStayRequestApi = (stay, fields) =>
	request(HOTEL_ENDPOINTS.addStayRequest, {
		stay,
		category: fields.category,
		value: fields.value || null,
		priority: fields.priority,
		room_feature: fields.roomFeature || null,
	});
export const closeStayRequestApi = (request_, status, notes = null) =>
	request(HOTEL_ENDPOINTS.closeStayRequest, { request: request_, status, notes });
export const copyRequestToProfileApi = (request_) =>
	request(HOTEL_ENDPOINTS.copyRequestToProfile, { request: request_ });
export const applySuggestionApi = (stay, key, evidence) =>
	request(HOTEL_ENDPOINTS.applySuggestion, { stay, key, evidence });
export const saveSuggestionApi = (guestProfile, key, evidence, stay) =>
	request(HOTEL_ENDPOINTS.saveSuggestion, { guest_profile: guestProfile, key, evidence, stay });
export const dismissSuggestionApi = (guestProfile, key, evidence, stay) =>
	request(HOTEL_ENDPOINTS.dismissSuggestion, {
		guest_profile: guestProfile,
		key,
		evidence,
		stay,
	});
export const fetchHistoryMatchesApi = () => request(HOTEL_ENDPOINTS.historyMatches);
export const findHistoryMatchesApi = () => request(HOTEL_ENDPOINTS.findHistoryMatches);
export const reviewHistoryMatchApi = (match, confirm) =>
	request(HOTEL_ENDPOINTS.reviewHistoryMatch, { match, confirm: confirm ? 1 : 0 });
