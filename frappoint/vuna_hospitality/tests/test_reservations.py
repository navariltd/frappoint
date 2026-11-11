"""F5 Booking, hold, and confirm."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, getdate, now_datetime

from frappoint.vuna_hospitality.api.reservations import get_booking_desk_context
from frappoint.vuna_hospitality.services import inventory, reservations
from frappoint.vuna_hospitality.services.feature_flag import HospitalityDisabledError
from frappoint.vuna_hospitality.services.inventory import InventoryConflictError, InventoryUnavailableError
from frappoint.vuna_hospitality.services.rates import generate_from_season
from frappoint.vuna_hospitality.services.reservations import (
	HoldExpiredError,
	HoldRefusedError,
	booking_status,
	cancel,
	confirm,
	expire_hold,
	expire_holds,
	hold,
)
from frappoint.vuna_hospitality.services.status_commands import InvalidTransitionError
from frappoint.vuna_hospitality.tests.test_inventory import _like_mariadb_11_8
from frappoint.vuna_hospitality.tests.utils import (
	hospitality_enabled,
	make_test_property,
	make_test_rate_setup,
	make_test_season,
	run_concurrently,
)


def make_booking_fixtures(code: str, rooms: int = 2):
	"""A property with one STD room type, a BAR plan priced for 30 nights, and a guest."""
	prop, _rooms = make_test_property(code=code, room_types={"STD": rooms})
	plan = make_test_rate_setup(code)
	today = getdate(prop.business_date)
	generate_from_season(
		make_test_season(plan, today, today + timedelta(days=29), {f"{code}-STD": (10000, 12000)}).name
	)
	if not frappe.db.exists("UTM Source", "Phone Calls"):
		frappe.get_doc({"doctype": "UTM Source", "name": "Phone Calls"}).insert(ignore_permissions=True)
	guest = frappe.get_doc(
		{"doctype": "Guest Profile", "first_name": "Wanjiku", "last_name": f"Test{code}"}
	).insert(ignore_permissions=True)
	return prop, plan, guest


def stay_request(code, plan, guest, arrival, nights=2, **extra):
	return {
		"room_type": f"{code}-STD",
		"rate_plan": plan.name,
		"arrival": arrival,
		"departure": arrival + timedelta(days=nights),
		"lead_guest": guest.name,
		"adults": 2,
		**extra,
	}


def counters(code, night):
	return frappe.db.get_value(
		"Room Type Inventory Day", inventory.row_name(f"{code}-STD", night), ["held", "sold", "available"]
	)


class ReservationTestCase(IntegrationTestCase):
	CODE = "RSV"

	def setUp(self):
		frappe.db.savepoint("reservation_test")
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE)
		self.today = getdate(self.prop.business_date)
		self.arrival = self.today + timedelta(days=3)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="reservation_test")

	def hold(self, nights=2, arrival=None, **extra):
		return hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, arrival or self.arrival, nights, **extra)],
			booking_details={"booking_source": "Phone Calls", "booker_guest_profile": self.guest.name},
		)

	def stay(self, summary, index=0):
		return frappe.get_doc("Stay Reservation", summary["stays"][index]["name"])


class TestHold(ReservationTestCase):
	def test_hold_creates_the_records_and_takes_held_rooms(self):
		summary = self.hold(nights=2)
		stay = self.stay(summary)

		self.assertEqual(summary["status"], "Option")
		self.assertEqual((stay.status, stay.nights, stay.adults), ("Held", 2, 2))
		self.assertTrue(stay.hold_expires_at)
		self.assertTrue(stay.name.startswith(f"SR-{self.CODE}-"))
		self.assertEqual(summary["name"][:7], f"HB-{self.CODE}-")

		occupancy = frappe.get_doc("Room Occupancy", stay.room_occupancy)
		self.assertEqual(occupancy.allocation_state, "Held")
		self.assertTrue(
			frappe.db.exists("Occupancy Membership", {"stay_reservation": stay.name, "reason": "Initial"})
		)

		nights = frappe.get_all(
			"Stay Rate Night",
			filters={"stay_reservation": stay.name},
			fields=["night_date", "room_rate", "posting_state"],
			order_by="night_date",
		)
		self.assertEqual([n.posting_state for n in nights], ["Pending", "Pending"])
		self.assertEqual(sum(n.room_rate for n in nights), stay.total_amount)
		self.assertEqual(summary["total_amount"], stay.total_amount)
		self.assertIn('"policy_type": "Cancellation"', stay.cancellation_policy_snapshot)

		self.assertEqual(counters(self.CODE, self.arrival)[:2], (1, 0))
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log", {"reference_name": stay.name, "event_type": "Hold Placed"}
			)
		)

	def test_inventory_rebuild_agrees_with_the_bookings(self):
		self.hold()
		confirm(self.stay(self.hold(arrival=self.arrival + timedelta(days=1))).name)
		self.assertEqual(inventory.reconcile(self.CODE), [])

	def test_hold_refuses_what_the_quote_refuses(self):
		with self.assertRaises(HoldRefusedError):
			self.hold(nights=40)  # past max_stay_nights and the priced season
		with self.assertRaises(HoldRefusedError):
			self.hold(arrival=self.today - timedelta(days=1))
		with self.assertRaises(HoldRefusedError):
			self.hold(adults=5)

	def test_last_room_is_not_held_twice(self):
		self.hold()
		self.hold()
		with self.assertRaises(InventoryUnavailableError):
			self.hold()

	def test_do_not_rent_guest_is_refused(self):
		self.guest.update({"restriction_flag": 1, "restriction_reason": "Unpaid bill"})
		self.guest.save()
		with self.assertRaises(HoldRefusedError):
			self.hold()

	def test_multi_room_hold_is_all_or_nothing(self):
		requests = [stay_request(self.CODE, self.plan, self.guest, self.arrival) for _ in range(3)]
		with self.assertRaises(InventoryUnavailableError):
			hold(self.CODE, requests, booking_details={"booking_source": "Phone Calls"})
		self.assertFalse(frappe.db.exists("Stay Reservation", {"property": self.CODE}))

	def test_stays_can_be_added_to_an_existing_booking(self):
		first = self.hold()
		second = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, self.arrival)],
			booking=first["name"],
		)
		self.assertEqual(second["name"], first["name"])
		self.assertEqual(second["stay_count"], 2)

	def test_records_cannot_be_created_or_edited_outside_the_service(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Hotel Booking", "property": self.CODE, "booking_source": "Phone Calls"}
			).insert()
		stay = self.stay(self.hold())
		stay.departure_date = stay.departure_date + timedelta(days=1)
		with self.assertRaises(frappe.ValidationError):
			stay.save()
		stay.reload()
		stay.status = "Confirmed"
		with self.assertRaises(InvalidTransitionError):
			stay.save()


class TestConfirmAndCancel(ReservationTestCase):
	def test_confirm_moves_rooms_from_held_to_sold(self):
		summary = confirm(self.stay(self.hold()).name)
		stay = self.stay(summary)
		self.assertEqual((summary["status"], stay.status), ("Confirmed", "Confirmed"))
		self.assertIsNone(stay.hold_expires_at)
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", stay.room_occupancy, "allocation_state"), "Confirmed"
		)
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (0, 1))
		# Confirming again is harmless.
		confirm(stay.name)
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (0, 1))

	def test_cancel_a_hold_and_a_confirmed_stay(self):
		held = self.stay(self.hold())
		confirmed = self.stay(confirm(self.stay(self.hold()).name))
		self.assertEqual(counters(self.CODE, self.arrival), (1, 1, 0))

		with self.assertRaises(frappe.ValidationError):
			cancel(held.name, "")
		cancel(held.name, "Guest changed plans")
		cancel(confirmed.name, "Duplicate booking")

		self.assertEqual(counters(self.CODE, self.arrival), (0, 0, 2))
		self.assertEqual(
			frappe.db.get_value("Stay Reservation", confirmed.name, "cancellation_reason"),
			"Duplicate booking",
		)
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", held.room_occupancy, "allocation_state"), "Cancelled"
		)
		self.assertEqual(
			set(
				frappe.get_all(
					"Stay Rate Night", filters={"stay_reservation": held.name}, pluck="posting_state"
				)
			),
			{"Cancelled"},
		)
		cancel(held.name, "again")  # already cancelled: nothing more is released
		self.assertEqual(counters(self.CODE, self.arrival), (0, 0, 2))

	def test_booking_status_follows_its_stays(self):
		self.assertEqual(booking_status(["Held", "Held"]), "Option")
		self.assertEqual(booking_status(["Held", "Confirmed"]), "Confirmed")
		self.assertEqual(booking_status(["Confirmed", "Cancelled"]), "Partly Cancelled")
		self.assertEqual(booking_status(["Cancelled", "Expired"]), "Cancelled")

		requests = [stay_request(self.CODE, self.plan, self.guest, self.arrival) for _ in range(2)]
		summary = hold(self.CODE, requests, booking_details={"booking_source": "Phone Calls"})
		first, second = (stay["name"] for stay in summary["stays"])
		confirm(first)
		self.assertEqual(cancel(second, "One room is enough")["status"], "Partly Cancelled")
		self.assertEqual(cancel(first, "Trip off")["status"], "Cancelled")


class TestHoldExpiry(ReservationTestCase):
	def expire_now(self, stay):
		frappe.db.set_value(
			"Stay Reservation", stay.name, "hold_expires_at", add_to_date(now_datetime(), minutes=-1)
		)

	def test_expired_hold_releases_its_rooms_exactly_once(self):
		stay = self.stay(self.hold())
		self.assertFalse(expire_hold(stay.name))  # not expired yet
		self.expire_now(stay)

		# The job commits after each hold; keep this test inside its savepoint.
		with hospitality_enabled(True), patch.object(frappe.db, "commit"):
			# Other expired holds on the site may be released too; this one must be among them.
			self.assertGreaterEqual(expire_holds(), 1)
			self.assertEqual(expire_holds(), 0)
		self.assertFalse(expire_hold(stay.name))

		stay.reload()
		self.assertEqual(stay.status, "Expired")
		self.assertEqual(
			frappe.db.get_value("Room Occupancy", stay.room_occupancy, "allocation_state"), "Released"
		)
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (0, 0))
		self.assertEqual(
			frappe.db.count(
				"Hospitality Event Log", {"reference_name": stay.name, "event_type": "Hold Expired"}
			),
			1,
		)

	def test_an_expired_hold_cannot_be_confirmed(self):
		stay = self.stay(self.hold())
		self.expire_now(stay)
		with self.assertRaises(HoldExpiredError):
			confirm(stay.name)

	def test_a_confirmed_stay_does_not_expire(self):
		stay = self.stay(confirm(self.stay(self.hold()).name))
		self.expire_now(stay)
		self.assertFalse(expire_hold(stay.name))
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (0, 1))

	def test_expiry_job_is_off_while_hospitality_is_disabled(self):
		stay = self.stay(self.hold())
		self.expire_now(stay)
		with hospitality_enabled(False), patch.object(frappe.db, "commit"):
			expire_holds()
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Held")


class TestReservationApi(ReservationTestCase):
	def test_api_requires_hospitality_enabled(self):
		with hospitality_enabled(False), self.assertRaises(HospitalityDisabledError):
			get_booking_desk_context()
		with hospitality_enabled(True):
			context = get_booking_desk_context()
		self.assertIn(self.CODE, [p.name for p in context["properties"]])
		self.assertIn("Phone Calls", context["booking_sources"])

	def test_lock_conflict_becomes_a_retryable_error(self):
		stay = self.stay(self.hold())
		with patch.object(frappe.db, "get_value", side_effect=frappe.QueryDeadlockError("1020")):
			with self.assertRaises(InventoryConflictError):
				reservations._lock_stay(stay.name)


class ConcurrentReservationTestCase(IntegrationTestCase):
	"""Racing requests need committed data on separate connections; everything is removed after."""

	CODE = "RSVR"
	ROOMS = 1

	def setUp(self):
		self._cleanup()
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=self.ROOMS)
		self.arrival = getdate(self.prop.business_date) + timedelta(days=2)
		frappe.db.commit()

	def tearDown(self):
		self._cleanup()

	def _cleanup(self):
		frappe.db.rollback()
		code = self.CODE
		for doctype in (
			"Stay Rate Night",
			"Occupancy Membership",
			"Stay Reservation",
			"Room Occupancy",
			"Hotel Booking",
			"Room Type Inventory Day",
			"Room Rate Day",
			"Rate Season",
			"Rate Plan",
			"Hotel Policy",
			"Hotel Room",
			"Room Type",
		):
			frappe.db.delete(doctype, {"property": code})
		frappe.db.delete("Rate Season Rate", {"room_type": ["like", f"{code}-%"]})
		frappe.db.delete("Guest Profile", {"last_name": f"Test{code}"})
		frappe.db.delete("Hospitality Event Log", {"property": code})
		frappe.db.delete("Hotel Property", {"name": code})
		frappe.db.commit()

	def hold_request(self):
		def run():
			_like_mariadb_11_8()
			return inventory.run_with_inventory_retry(
				lambda: hold(
					self.CODE,
					[stay_request(self.CODE, self.plan, self.guest, self.arrival)],
					booking_details={"booking_source": "Phone Calls"},
				)
			)

		return run


class TestConcurrentHold(ConcurrentReservationTestCase):
	def test_two_agents_cannot_hold_the_last_room(self):
		"""Scenario 9: only the permitted inventory is sold."""
		results = run_concurrently(self.hold_request(), self.hold_request())
		winners = [r for r in results if r.ok]
		self.assertEqual(len(winners), 1, [r.error for r in results])
		self.assertIsInstance(next(r.error for r in results if not r.ok), InventoryUnavailableError)
		self.assertEqual(frappe.db.count("Stay Reservation", {"property": self.CODE}), 1)
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (1, 0))


class TestRacingCommands(ConcurrentReservationTestCase):
	CODE = "RSVX"

	def held_stay(self):
		stay = self.hold_request()()["stays"][0]["name"]
		frappe.db.commit()
		return stay

	def command(self, fn):
		def run():
			_like_mariadb_11_8()
			return inventory.run_with_inventory_retry(fn)

		return run

	def test_two_expiry_runs_release_a_hold_once(self):
		stay = self.held_stay()
		frappe.db.set_value(
			"Stay Reservation", stay, "hold_expires_at", add_to_date(now_datetime(), minutes=-1)
		)
		frappe.db.commit()

		results = run_concurrently(
			self.command(lambda: expire_hold(stay)), self.command(lambda: expire_hold(stay))
		)
		self.assertEqual(sorted(r.value for r in results), [False, True], [r.error for r in results])
		frappe.db.rollback()
		self.assertEqual(counters(self.CODE, self.arrival)[:2], (0, 0))
		self.assertEqual(
			frappe.db.count("Hospitality Event Log", {"reference_name": stay, "event_type": "Hold Expired"}),
			1,
		)

	def test_confirm_racing_cancel_leaves_consistent_inventory(self):
		stay = self.held_stay()
		results = run_concurrently(
			self.command(lambda: confirm(stay)), self.command(lambda: cancel(stay, "Changed plans"))
		)
		confirmed, cancelled = results
		# Cancel always succeeds: it cancels the hold, or the stay the confirm just confirmed. A
		# confirm that runs after the cancel is refused.
		self.assertTrue(cancelled.ok, cancelled.error)
		if not confirmed.ok:
			self.assertIsInstance(confirmed.error, InvalidTransitionError)
		frappe.db.rollback()
		status = frappe.db.get_value("Stay Reservation", stay, "status")
		held, sold, _available = counters(self.CODE, self.arrival)
		self.assertEqual(status, "Cancelled")
		self.assertEqual((held, sold), (0, 0))
		self.assertEqual(inventory.reconcile(self.CODE), [])
