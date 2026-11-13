import { createResource } from "frappe-ui";

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
};

const unwrapPayload = (payload) => payload?.message ?? payload ?? null;

async function request(url, params = {}) {
	const resource = createResource({ url, auto: false });
	const response = await resource.fetch(params);
	return unwrapPayload(response ?? resource.data);
}

/** The server's message for a failed call, without the traceback. */
export function hotelErrorMessage(error) {
	const messages = error?.messages?.filter(Boolean);
	if (messages?.length) return messages.join(" ");
	return error?.message || "Something went wrong. Please try again.";
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
export const fetchRecentBookingsApi = (property) =>
	request(HOTEL_ENDPOINTS.recentBookings, { property });

// Front desk (F6)
export const fetchFrontDeskTodayApi = (property) =>
	request(HOTEL_ENDPOINTS.frontDeskToday, { property });
export const fetchStayApi = (stay) => request(HOTEL_ENDPOINTS.stay, { stay });
export const fetchAssignableRoomsApi = (stay) =>
	request(HOTEL_ENDPOINTS.assignableRooms, { stay });
export const fetchMoveReasonsApi = () => request(HOTEL_ENDPOINTS.moveReasons);
export const assignRoomApi = (stay, room, lock = false) =>
	request(HOTEL_ENDPOINTS.assignRoom, { stay, room, lock: lock ? 1 : 0 });
export const unassignRoomApi = (stay, reason) =>
	request(HOTEL_ENDPOINTS.unassignRoom, { stay, reason });
export const setRoomLockApi = (stay, locked, reason) =>
	request(HOTEL_ENDPOINTS.setRoomLock, { stay, locked: locked ? 1 : 0, reason });
export const moveRoomApi = (stay, room, moveReason) =>
	request(HOTEL_ENDPOINTS.moveRoom, { stay, room, move_reason: moveReason });
export const checkInApi = (stay, room) =>
	request(HOTEL_ENDPOINTS.checkIn, { stay, room: room || null });
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
export const addRoutingRuleApi = ({ stay, targetFolio, route, chargeCode, itemGroup, notes }) =>
	request(HOTEL_ENDPOINTS.addRoutingRule, {
		stay,
		target_folio: targetFolio,
		route,
		charge_code: chargeCode || null,
		item_group: itemGroup || null,
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
