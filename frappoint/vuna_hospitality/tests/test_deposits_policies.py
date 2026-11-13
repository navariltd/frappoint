"""F12 Deposits, policies, routing, and house accounts."""

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

import frappe

from frappoint.vuna_hospitality.api import folios as folios_api
from frappoint.vuna_hospitality.services import (
	cashiering,
	deposits,
	folio,
	house_accounts,
	night_audit,
	policies,
	post_stay,
	reservations,
	routing,
	settlement,
)
from frappoint.vuna_hospitality.services.front_desk import (
	CheckInRefusedError,
	assign_room,
	check_in,
	check_out,
	depart_early,
	register_guest,
)
from frappoint.vuna_hospitality.services.inventory import InventoryUnavailableError
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.tests.test_cashiering import MPESA
from frappoint.vuna_hospitality.tests.test_folio import make_item, make_item_group, make_user
from frappoint.vuna_hospitality.tests.test_reservations import counters, stay_request
from frappoint.vuna_hospitality.tests.test_settlement import (
	FACIAL,
	SettlementTestCase,
	make_company_customer,
)
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

FEE_ITEM = "HSP-TEST-POLICY-FEE"
FEE_CODE = "TFEE"


class PolicyTestCase(SettlementTestCase):
	"""An in-house stay in room 101 (from the base class), a fee charge code, and helpers for
	stays booked with policies."""

	CODE = "PLC"

	def setUp(self):
		super().setUp()
		make_item_group("HSP Test Fees")
		make_item(FEE_ITEM, "HSP Test Fees")
		if not frappe.db.exists("Charge Code", FEE_CODE):
			frappe.get_doc(
				{
					"doctype": "Charge Code",
					"code": FEE_CODE,
					"description": "Test policy fee",
					"transaction_type": "Revenue",
					"item": FEE_ITEM,
					"print_group": "Fees",
				}
			).insert(ignore_permissions=True)
		frappe.db.set_value("Hotel Property", self.CODE, "policy_fee_charge_code", FEE_CODE)

	def policy(self, policy_type, **values):
		return (
			frappe.get_doc(
				{
					"doctype": "Hotel Policy",
					"property": self.CODE,
					"policy_name": f"{policy_type} {frappe.generate_hash(length=4)}",
					"policy_type": policy_type,
					**values,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def use_policies(self, **policies_by_field):
		"""Set the rate plan's policies; stays held from now on are booked with them."""
		self.plan.reload()
		self.plan.update(policies_by_field)
		self.plan.save()

	def booked(self, arrival, nights=2):
		summary = reservations.hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, arrival, nights)],
			booking_details={"booking_source": "Phone Calls"},
		)
		name = summary["stays"][0]["name"]
		reservations.confirm(name)
		return frappe.get_doc("Stay Reservation", name)

	def arrive(self, stay, room="102"):
		assign_room(stay.name, f"{self.CODE}-{room}")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def nights(self, stay, state=None):
		filters = {"stay_reservation": stay.name}
		if state:
			filters["posting_state"] = state
		return frappe.get_all(
			"Stay Rate Night",
			filters=filters,
			fields=["night_date", "total", "posting_state"],
			order_by="night_date",
		)

	def fees(self, stay):
		return policies.fee_lines(stay.name)

	def folio_of(self, stay):
		return frappe.db.get_value("Stay Reservation", stay.name, "default_folio")

	def set_business_date(self, date):
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", date)

	@contextmanager
	def as_user(self, role):
		user = make_user(f"f12-{role.lower().replace(' ', '-')}@example.com", role)
		frappe.set_user(user)
		try:
			yield user
		finally:
			frappe.set_user("Administrator")


class TestCancellationFees(PolicyTestCase):
	def setUp(self):
		super().setUp()
		self.use_policies(
			cancellation_policy=self.policy(
				"Cancellation", free_until_hours_before_arrival=48, fee_type="First Night"
			)
		)

	def test_cancelling_before_the_penalty_window_is_free(self):
		stay = self.booked(self.today + timedelta(days=5))
		reservations.cancel(stay.name, "Change of plans")
		self.assertEqual(self.fees(stay), [])
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio_of(stay), "status"), "Closed")

	def test_cancelling_inside_the_window_charges_the_first_night_once(self):
		stay = self.booked(self.today + timedelta(days=1))
		first_night = self.nights(stay)[0].total
		quote = reservations.booking_summary(stay.hotel_booking)["stays"][0]
		self.assertEqual(quote["cancellation_fee"], first_night)

		reservations.cancel(stay.name, "Change of plans")
		reservations.cancel(stay.name, "Change of plans")

		fees = self.fees(stay)
		self.assertEqual(len(fees), 1)
		self.assertEqual(fees[0].gross_amount, first_night)
		self.assertTrue(fees[0].posting_key.startswith(f"fee:{stay.name}:"))
		self.assertTrue(fees[0].posting_key.endswith(":cancellation"))
		# The fee waits on the open folio for payment; the rooms and nights are gone.
		self.assertEqual(frappe.db.get_value("Guest Folio", fees[0].guest_folio, "status"), "Open")
		self.assertEqual({night.posting_state for night in self.nights(stay)}, {"Cancelled"})

	def test_only_a_front_desk_manager_waives_the_fee(self):
		stay = self.booked(self.today + timedelta(days=1))
		with self.as_user("Reservations Agent"), self.assertRaises(frappe.PermissionError):
			reservations.cancel(stay.name, "Guest ill", waive_fee=True, waive_reason="Doctor's note")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Confirmed")

		reservations.cancel(stay.name, "Guest ill", waive_fee=True, waive_reason="Doctor's note")
		self.assertEqual(self.fees(stay), [])
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": stay.name, "event_type": "Policy Fee Waived", "reason": "Doctor's note"},
			)
		)

	def test_a_fee_needs_a_charge_code_to_post(self):
		frappe.db.set_value("Hotel Property", self.CODE, "policy_fee_charge_code", None)
		stay = self.booked(self.today + timedelta(days=1))
		with self.assertRaises(policies.PolicyFeeError):
			reservations.cancel(stay.name, "Change of plans")


class TestDeposits(PolicyTestCase):
	def setUp(self):
		super().setUp()
		self.use_policies(
			deposit_policy=self.policy("Deposit", deposit_type="Fixed Amount", deposit_value=15000),
			cancellation_policy=self.policy(
				"Cancellation", free_until_hours_before_arrival=48, fee_type="First Night"
			),
		)

	def deposit_of(self, stay):
		return deposits.deposit_details(stay.name)

	def test_confirming_asks_for_the_deposit_on_the_default_folio(self):
		stay = self.booked(self.today + timedelta(days=3))
		deposit = self.deposit_of(stay)
		self.assertEqual(deposit["status"], "Requested")
		self.assertEqual(deposit["required_amount"], 15000)
		self.assertEqual(deposit["guest_folio"], self.folio_of(stay))
		self.assertEqual(deposit["due_date"], self.today)

	def test_a_cash_deposit_is_an_advance_payment_entry(self):
		stay = self.booked(self.today + timedelta(days=3))
		payment = deposits.take_deposit(self.deposit_of(stay)["name"], mode_of_payment="HSP Test Cash")
		deposit = self.deposit_of(stay)
		self.assertEqual((deposit["status"], deposit["held"]), ("Received", 15000))
		entry = frappe.db.get_value("Folio Payment", payment, "payment_entry")
		self.assertEqual(
			frappe.db.get_value("Payment Entry", entry, ["payment_type", "paid_amount"]), ("Receive", 15000)
		)
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio_of(stay), "balance"), -15000)

	def test_an_mpesa_deposit_is_received_once_by_its_callback(self):
		stay = self.booked(self.today + timedelta(days=3))
		with (
			patch.object(cashiering, "_request_phone_payment"),
			patch.object(cashiering, "gateway_mode_of_payment", return_value=MPESA),
		):
			payment = deposits.take_deposit(
				self.deposit_of(stay)["name"], payment_gateway="Mpesa-Test", phone="0712345678"
			)
		self.assertEqual(self.deposit_of(stay)["status"], "Requested")
		self.callback(payment)
		self.callback(payment)
		deposit = self.deposit_of(stay)
		self.assertEqual((deposit["status"], deposit["held"]), ("Received", 15000))
		self.assertEqual(len(deposit["payments"]), 1)

	def test_check_in_needs_the_deposit_or_a_waiver(self):
		stay = self.booked(self.today)
		with self.assertRaises(CheckInRefusedError):
			self.arrive(stay)
		deposits.take_deposit(self.deposit_of(stay)["name"], 5000, mode_of_payment="HSP Test Cash")
		self.assertEqual(self.deposit_of(stay)["status"], "Partly Paid")
		with self.assertRaises(CheckInRefusedError):
			self.arrive(stay)

		with self.as_user("Front Desk Agent"), self.assertRaises(frappe.PermissionError):
			deposits.waive(self.deposit_of(stay)["name"], "Regular guest")
		deposits.waive(self.deposit_of(stay)["name"], "Regular guest")
		self.assertEqual(self.arrive(stay).status, "In House")

	def test_the_deposit_pays_the_invoice_at_settlement(self):
		stay = self.booked(self.today)
		deposits.take_deposit(self.deposit_of(stay)["name"], mode_of_payment="HSP Test Cash")
		stay = self.arrive(stay)
		self.set_business_date(self.today + timedelta(days=1))
		folio_name = self.folio_of(stay)
		# Check-out posts the first night; the guest pays what the deposit doesn't cover, or gets
		# back what it covered twice.
		check_out(stay.name, override_reason="Settles at the desk")
		owing = frappe.db.get_value("Guest Folio", folio_name, "balance")
		if owing > 0:
			self.pay(owing, folio_name=folio_name)
		elif owing < 0:
			payment = self.deposit_of(stay)["payments"][0]
			cashiering.refund(payment, {folio_name: -owing}, reason="Deposit over the bill")
		result = settlement.settle(folio_name)
		self.assertEqual(result["status"], "Closed")
		self.assertEqual(self.deposit_of(stay)["status"], "Applied")
		invoice = frappe.get_doc("Sales Invoice", result["sales_invoice"])
		self.assertEqual(invoice.outstanding_amount, 0)

	def test_cancelling_in_the_window_forfeits_the_deposit_and_refunds_only_the_excess(self):
		"""Scenario 34."""
		stay = self.booked(self.today + timedelta(days=1))
		fee = self.nights(stay)[0].total
		deposit = self.deposit_of(stay)["name"]
		deposits.take_deposit(deposit, mode_of_payment="HSP Test Cash")

		reservations.cancel(stay.name, "Change of plans")

		details = self.deposit_of(stay)
		self.assertEqual(details["status"], "Forfeited")
		self.assertEqual(details["refunded"], 15000 - fee)
		self.assertEqual(details["held"], fee)
		folio_row = frappe.db.get_value(
			"Guest Folio", self.folio_of(stay), ["status", "balance", "sales_invoice"], as_dict=True
		)
		self.assertEqual((folio_row.status, folio_row.balance), ("Closed", 0))
		invoice = frappe.get_doc("Sales Invoice", folio_row.sales_invoice)
		self.assertEqual((invoice.grand_total, invoice.outstanding_amount), (fee, 0))
		self.assertEqual([row.item_code for row in invoice.items], [FEE_ITEM])
		refund = frappe.get_all(
			"Folio Payment", filters={"refund_of": details["payments"][0]}, fields=["amount", "payment_entry"]
		)
		self.assertEqual([row.amount for row in refund], [15000 - fee])
		self.assertEqual(frappe.db.get_value("Payment Entry", refund[0].payment_entry, "payment_type"), "Pay")

	def test_without_a_shift_the_excess_waits_for_a_cashier(self):
		stay = self.booked(self.today + timedelta(days=1))
		fee = self.nights(stay)[0].total
		deposits.take_deposit(self.deposit_of(stay)["name"], mode_of_payment="HSP Test Cash")
		with patch.object(cashiering, "current_shift", return_value=None):
			reservations.cancel(stay.name, "Change of plans")
		self.assertEqual(self.deposit_of(stay)["status"], "Received")
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio_of(stay), "balance"), fee - 15000)
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": stay.name, "event_type": "Deposit Follow-up"}
			)
		)

	def test_cancelling_releases_a_deposit_nothing_was_paid_on(self):
		stay = self.booked(self.today + timedelta(days=5))
		reservations.cancel(stay.name, "Change of plans")
		self.assertEqual(self.deposit_of(stay)["status"], "Released")
		reservations.reinstate(stay.name, "Guest rebooked")
		deposit = self.deposit_of(stay)
		self.assertEqual((deposit["status"], deposit["due_date"]), ("Requested", self.today))

	def test_an_unpaid_deposit_releases_the_stay_when_due(self):
		self.plan.reload()
		frappe.db.set_value("Hotel Policy", self.plan.deposit_policy, "release_if_unpaid", 1)
		stay = self.booked(self.today + timedelta(days=3))
		self.assertEqual(deposits.overdue(self.CODE, self.today), [self.deposit_of(stay)["name"]])

		self.assertTrue(deposits.release(self.deposit_of(stay)["name"]))

		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Cancelled")
		self.assertEqual(self.deposit_of(stay)["status"], "Released")
		# Releasing for non-payment charges no fee, even inside the window.
		self.assertEqual(self.fees(stay), [])


class TestNoShows(PolicyTestCase):
	def setUp(self):
		super().setUp()
		self.use_policies(no_show_policy=self.policy("No-show", fee_type="First Night"))

	def test_a_guest_who_never_arrives_is_a_no_show_with_its_fee(self):
		stay = self.booked(self.today)
		first_night = self.nights(stay)[0].total
		sold_before = counters(self.CODE, self.today)[1]

		self.assertTrue(reservations.mark_no_show(stay.name, self.today))
		self.assertFalse(reservations.mark_no_show(stay.name, self.today))

		stay.reload()
		self.assertEqual(stay.status, "No Show")
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", stay.room_occupancy, "allocation_state"), "Released"
		)
		self.assertEqual(counters(self.CODE, self.today)[1], sold_before - 1)
		self.assertEqual({night.posting_state for night in self.nights(stay)}, {"Cancelled"})
		fees = self.fees(stay)
		self.assertEqual(
			[(fee.gross_amount, fee.posting_key.split(":")[-1]) for fee in fees], [(first_night, "no-show")]
		)

	def test_night_audit_marks_no_shows(self):
		stay = self.booked(self.today)
		with (
			hospitality_enabled(True),
			patch.object(frappe, "enqueue"),
			patch.object(frappe.db, "commit"),
			patch.object(night_audit, "is_job_enqueued", return_value=False),
		):
			run = night_audit.start_night_audit(self.CODE)
			self.assertEqual(night_audit.execute_run(run), "Completed")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "No Show")
		stage = frappe.get_all(
			"Night Audit Run Stage",
			filters={"parent": run, "stage": night_audit.MARK_NO_SHOWS},
			fields=["status", "posted"],
		)[0]
		self.assertEqual((stage.status, stage.posted), ("Completed", 1))
		# The in-house stay from the base class isn't touched.
		self.assertEqual(frappe.db.get_value("Stay Reservation", self.stay.name, "status"), "In House")


class TestReinstatement(PolicyTestCase):
	"""Scenario 14."""

	def setUp(self):
		super().setUp()
		self.use_policies(
			cancellation_policy=self.policy(
				"Cancellation", free_until_hours_before_arrival=48, fee_type="First Night"
			)
		)

	def test_a_reinstated_stay_takes_its_rooms_again_and_its_fee_is_reversed(self):
		arrival = self.today + timedelta(days=1)
		stay = self.booked(arrival)
		sold = counters(self.CODE, arrival)[1]
		reservations.cancel(stay.name, "Change of plans")
		self.assertEqual(counters(self.CODE, arrival)[1], sold - 1)
		old_occupancy = stay.room_occupancy

		reservations.reinstate(stay.name, "Guest rebooked")

		stay.reload()
		self.assertEqual(stay.status, "Confirmed")
		self.assertNotEqual(stay.room_occupancy, old_occupancy)
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", stay.room_occupancy, "allocation_state"), "Confirmed"
		)
		self.assertEqual(counters(self.CODE, arrival)[1], sold)
		self.assertEqual({night.posting_state for night in self.nights(stay)}, {"Pending"})
		self.assertEqual(self.fees(stay), [])
		folio_row = frappe.db.get_value(
			"Guest Folio", self.folio_of(stay), ["status", "balance"], as_dict=True
		)
		self.assertEqual((folio_row.status, folio_row.balance), ("Open", 0))

		# Cancelled again, the stay is charged again under a new key.
		reservations.cancel(stay.name, "Cancelled again")
		self.assertEqual([fee.posting_key.split(":")[-1] for fee in self.fees(stay)], ["cancellation-2"])

	def test_a_full_night_refuses_reinstatement(self):
		arrival = self.today + timedelta(days=1)
		stay = self.booked(arrival)
		reservations.cancel(stay.name, "Change of plans")
		# The base class's stay holds one of the two rooms tonight and tomorrow; sell the other.
		self.booked(arrival, nights=1)

		with self.assertRaises(InventoryUnavailableError):
			reservations.reinstate(stay.name, "Guest rebooked")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Cancelled")

	def test_a_no_show_is_reinstated_from_the_business_date(self):
		stay = self.booked(self.today, nights=3)
		reservations.mark_no_show(stay.name, self.today)
		self.set_business_date(self.today + timedelta(days=1))

		reservations.reinstate(stay.name, "Flight was delayed")

		stay.reload()
		self.assertEqual(
			(stay.status, stay.arrival_date, stay.nights), ("Confirmed", self.today + timedelta(days=1), 2)
		)
		states = {str(night.night_date): night.posting_state for night in self.nights(stay)}
		self.assertEqual(states[str(self.today)], "Cancelled")
		self.assertEqual(states[str(self.today + timedelta(days=1))], "Pending")

	def test_reinstating_needs_a_manager(self):
		stay = self.booked(self.today + timedelta(days=5))
		reservations.cancel(stay.name, "Change of plans")
		from frappoint.vuna_hospitality.api import reservations as reservations_api

		with (
			hospitality_enabled(True),
			self.as_user("Reservations Agent"),
			self.assertRaises(frappe.PermissionError),
		):
			reservations_api.reinstate_stay(stay.name, "Guest rebooked")


class TestEarlyDeparture(PolicyTestCase):
	"""Scenario 15."""

	def setUp(self):
		super().setUp()
		self.use_policies(
			early_departure_policy=self.policy("Early Departure", fee_type="Percentage of Stay", fee_value=50)
		)
		self.leaver = self.arrive(self.booked(self.today, nights=3))

	def test_leaving_early_charges_the_fee_and_gives_the_nights_back(self):
		given_up = [night.total for night in self.nights(self.leaver)][1:]
		tomorrow = self.today + timedelta(days=1)
		sold = counters(self.CODE, tomorrow)[1]

		fee = depart_early(self.leaver.name)

		expected = to_minor(sum(given_up), self.currency) // 2
		self.assertEqual(to_minor(fee["amount"], self.currency), expected)
		self.leaver.reload()
		self.assertEqual((self.leaver.departure_date, self.leaver.nights), (tomorrow, 1))
		self.assertEqual(counters(self.CODE, tomorrow)[1], sold - 1)
		pending = [night.night_date for night in self.nights(self.leaver, "Pending")]
		self.assertEqual(pending, [self.today])

		# The guest pays everything, including the fee, and checks out the next morning.
		self.set_business_date(tomorrow)
		night_audit.post_due_nights(self.leaver.name, tomorrow)
		folio_name = self.folio_of(self.leaver)
		self.pay(frappe.db.get_value("Guest Folio", folio_name, "balance"), folio_name=folio_name)
		check_out(self.leaver.name)
		self.assertEqual(self.nights(self.leaver, "Pending"), [])
		self.assertEqual(len(self.fees(self.leaver)), 1)

	def test_check_out_charges_the_fee_when_the_guest_just_leaves(self):
		self.set_business_date(self.today + timedelta(days=1))
		check_out(self.leaver.name, override_reason="Pays later")
		self.assertEqual(len(self.fees(self.leaver)), 1)
		self.assertEqual(self.nights(self.leaver, "Pending"), [])


class TestRouting(PolicyTestCase):
	def setUp(self):
		super().setUp()
		self.company_folio = settlement.add_folio(
			self.stay.name, "Safari Corp", payee_customer=make_company_customer("HSP Test Routing Corp")
		)

	def post_tonight(self):
		night = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": self.stay.name, "night_date": self.today},
			pluck="name",
		)[0]
		return night_audit.post_room_night(night, self.today)["name"]

	def test_room_charges_go_to_the_company_folio(self):
		pending = frappe.db.get_value("Guest Folio", self.folio, "pending_total")
		routing.add_rule(self.stay.name, self.company_folio, routing.ROOM_CHARGES)
		self.assertEqual(frappe.db.get_value("Guest Folio", self.company_folio, "pending_total"), pending)
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "pending_total"), 0)

		line = self.post_tonight()
		self.assertEqual(frappe.db.get_value("Folio Transaction", line, "guest_folio"), self.company_folio)
		# A charge staff post to the guest's folio stays there: an explicit destination wins.
		facial = self.facial(self.folio)
		self.assertEqual(frappe.db.get_value("Folio Transaction", facial, "guest_folio"), self.folio)

	def test_the_more_specific_rule_wins(self):
		third = settlement.add_folio(self.stay.name, "Room only")
		routing.add_rule(self.stay.name, self.company_folio, routing.ALL_CHARGES)
		routing.add_rule(self.stay.name, third, routing.CHARGE_CODE, charge_code="TROOM")
		self.assertEqual(frappe.db.get_value("Folio Transaction", self.post_tonight(), "guest_folio"), third)
		self.assertEqual(routing.destination(self.stay.name, "TMSG"), self.company_folio)

	def test_equal_rules_to_different_folios_stop_the_posting(self):
		third = settlement.add_folio(self.stay.name, "Other")
		routing.add_rule(self.stay.name, self.company_folio, routing.ALL_CHARGES)
		with self.assertRaises(routing.RoutingConflictError):
			routing.add_rule(self.stay.name, third, routing.ALL_CHARGES)

		# Two item-group rules can both match the room night: the second is refused at once,
		# because the stay's pending nights would have nowhere certain to go.
		room_group = frappe.db.get_value("Item", "HSP-TEST-ROOM-NIGHT", "item_group")
		routing.add_rule(self.stay.name, self.company_folio, routing.ITEM_GROUP, item_group="All Item Groups")
		with self.assertRaises(routing.RoutingConflictError):
			routing.add_rule(self.stay.name, third, routing.ITEM_GROUP, item_group=room_group)

	def test_removing_a_rule_sends_charges_home_again(self):
		rule = routing.add_rule(self.stay.name, self.company_folio, routing.ROOM_CHARGES)
		routing.remove_rule(rule, "Company pays only the first night")
		self.assertEqual(
			frappe.db.get_value("Folio Transaction", self.post_tonight(), "guest_folio"), self.folio
		)

	def test_a_fee_follows_the_rules(self):
		self.use_policies(
			cancellation_policy=self.policy(
				"Cancellation", free_until_hours_before_arrival=48, fee_type="Full Stay"
			)
		)
		stay = self.booked(self.today + timedelta(days=1))
		company = settlement.add_folio(stay.name, "Company", payee_customer="HSP Test Routing Corp")
		routing.add_rule(stay.name, company, routing.CHARGE_CODE, charge_code=FEE_CODE)
		reservations.cancel(stay.name, "Trip called off")
		self.assertEqual([fee.guest_folio for fee in self.fees(stay)], [company])

	def test_the_workspace_lists_and_removes_rules(self):
		with hospitality_enabled(True):
			details = folios_api.add_routing_rule(self.stay.name, self.company_folio, routing.ROOM_CHARGES)
			self.assertEqual(
				[rule["target_folio"] for rule in details["routing_rules"]], [self.company_folio]
			)
			details = folios_api.remove_routing_rule(details["routing_rules"][0]["name"], "Wrong folio")
			self.assertEqual(details["routing_rules"], [])


class TestHouseAccounts(PolicyTestCase):
	"""Scenario 28."""

	def test_a_non_residents_restaurant_charge_settles_on_a_house_account(self):
		inventory_before = frappe.get_all(
			"Room Type Inventory Day",
			filters={"room_type": f"{self.CODE}-STD"},
			fields=["name", "sold", "held"],
		)
		occupancies = frappe.db.count("Room Occupancy", {"property": self.CODE})
		customer = make_company_customer("HSP Test Conference Co")
		account = house_accounts.create(
			self.CODE, "Leadership Summit", account_type="Event", payee_customer=customer
		)
		folio_name = frappe.db.get_value("House Account", account, "current_folio")
		self.assertEqual(
			frappe.db.get_value("Guest Folio", folio_name, ["owner_type", "stay_reservation"]),
			("House Account", None),
		)

		charge = self.facial(folio_name)
		self.assertIsNone(frappe.db.get_value("Folio Transaction", charge, "stay_reservation"))
		result = self.settle_paid(folio_name)

		invoice = frappe.get_doc("Sales Invoice", result["sales_invoice"])
		self.assertEqual((invoice.customer, invoice.outstanding_amount), (customer, 0))
		# Occupancy statistics don't move: no inventory, no occupancy.
		self.assertEqual(
			frappe.get_all(
				"Room Type Inventory Day",
				filters={"room_type": f"{self.CODE}-STD"},
				fields=["name", "sold", "held"],
			),
			inventory_before,
		)
		self.assertEqual(frappe.db.count("Room Occupancy", {"property": self.CODE}), occupancies)

		# The account's next charge goes on a new folio; the settled one is kept.
		next_folio = house_accounts.ensure_folio(account)
		self.assertNotEqual(next_folio, folio_name)

	def test_a_closed_or_ended_account_takes_no_charges(self):
		account = house_accounts.create(
			self.CODE, "Old Event", account_type="Event", valid_to=self.today + timedelta(days=1)
		)
		folio_name = frappe.db.get_value("House Account", account, "current_folio")
		self.set_business_date(self.today + timedelta(days=2))
		with self.assertRaises(house_accounts.HouseAccountError):
			self.facial(folio_name)
		house_accounts.close(account, "Event over")
		self.assertEqual(frappe.db.get_value("House Account", account, "status"), "Closed")
		self.assertEqual(frappe.db.get_value("Guest Folio", folio_name, "status"), "Closed")

	def test_an_account_with_an_unsettled_folio_stays_open(self):
		account = house_accounts.create(self.CODE, "Staff Meals")
		self.facial(frappe.db.get_value("House Account", account, "current_folio"))
		with self.assertRaises(house_accounts.HouseAccountError):
			house_accounts.close(account, "No longer used")

	def test_the_workspace_shows_the_account(self):
		account = house_accounts.create(self.CODE, "Staff Meals")
		with hospitality_enabled(True):
			details = folios_api.get_house_account_folios(account)
		self.assertEqual(details["stay"]["lead_guest_name"], "Staff Meals")
		self.assertEqual(len(details["folios"]), 1)
		self.assertFalse(details["actions"]["can_open_house_folio"])


class TestPostStay(PolicyTestCase):
	"""Scenario 29."""

	def test_a_late_minibar_charge_posts_after_check_out_with_its_provenance(self):
		self.check_out()  # a day early, with the massage still owing, by a manager's override
		self.stay.reload()
		folio_row = frappe.db.get_value(
			"Guest Folio", self.folio, ["status", "post_stay_until"], as_dict=True
		)
		self.assertEqual(folio_row.status, "Post-Stay Open")
		# The property's window (2 days) counts from the day the guest left.
		self.assertEqual(folio_row.post_stay_until, self.stay.departure_date + timedelta(days=2))

		with self.assertRaises(folio.PostingError):
			folio.post_manual_charge(self.folio, FACIAL)
		with self.as_user("Front Desk Agent"), self.assertRaises(frappe.PermissionError):
			folio.post_manual_charge(self.folio, FACIAL, reason="Minibar count")
		line = folio.post_manual_charge(self.folio, FACIAL, reason="Minibar count")["name"]

		row = frappe.db.get_value(
			"Folio Transaction", line, ["stay_reservation", "room_number_snapshot", "reason"], as_dict=True
		)
		self.assertEqual(
			(row.stay_reservation, row.room_number_snapshot, row.reason),
			(self.stay.name, "101", "Minibar count"),
		)

	def test_after_the_window_paid_folios_close_and_owing_ones_wait(self):
		self.check_out()
		self.stay.reload()
		owing = settlement.add_folio(self.stay.name, "Damages")
		folio.post_manual_charge(owing, FACIAL, reason="Broken lamp")
		self.pay(self.balance(self.folio), folio_name=self.folio)
		idle = settlement.add_folio(self.stay.name, "Nothing")
		self.set_business_date(self.stay.departure_date + timedelta(days=3))

		with self.assertRaises(folio.FolioClosedError):
			folio.post_manual_charge(self.folio, FACIAL, reason="Too late")
		results = {name: post_stay.close_expired(name) for name in (self.folio, owing, idle)}

		self.assertEqual(results, {self.folio: "settled", owing: "owing", idle: "closed"})
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "status"), "Closed")
		self.assertTrue(frappe.db.get_value("Guest Folio", self.folio, "sales_invoice"))
		self.assertEqual(frappe.db.get_value("Guest Folio", owing, "status"), "Post-Stay Open")

	def test_an_invoiced_stay_opens_a_new_folio_for_a_late_charge(self):
		self.check_out()
		self.settle_paid()
		self.assertEqual(frappe.db.get_value("Guest Folio", self.folio, "status"), "Closed")
		with self.as_user("Front Desk Agent"), self.assertRaises(frappe.PermissionError):
			settlement.add_folio(self.stay.name, "Late charges")
		late = settlement.add_folio(self.stay.name, "Late charges")
		self.assertEqual(frappe.db.get_value("Guest Folio", late, "status"), "Post-Stay Open")
		self.assertEqual(
			frappe.db.get_value("Guest Folio", late, "payee_guest_profile"),
			frappe.db.get_value("Guest Folio", self.folio, "payee_guest_profile"),
		)
