"""F16 Tape chart."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api import tape_chart as tape_chart_api
from frappoint.vuna_hospitality.services import preferences, room_ranking, tape_chart
from frappoint.vuna_hospitality.services.front_desk import (
	RoomUnavailableError,
	assign_room,
	check_in,
	install_default_move_reasons,
	register_guest,
	set_room_lock,
)
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.services.tape_chart import DropRefusedError
from frappoint.vuna_hospitality.tests.test_folio import make_user
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled


class TapeChartTestCase(IntegrationTestCase):
	CODE = "TPC"

	def setUp(self):
		frappe.db.savepoint("tape_chart_test")
		# The endpoints are hospitality commands; CI's test site has the module off.
		self._hospitality = hospitality_enabled(True)
		self._hospitality.__enter__()
		self.prop, self.plan, self.guest = make_booking_fixtures(self.CODE, rooms=3)
		self.today = getdate(self.prop.business_date)
		install_default_move_reasons()
		for room in self.rooms():
			frappe.db.set_value("Hotel Room", room, "housekeeping_condition", "Clean")

	def tearDown(self):
		frappe.set_user("Administrator")
		self._hospitality.__exit__(None, None, None)
		frappe.db.rollback(save_point="tape_chart_test")

	def rooms(self):
		return [f"{self.CODE}-10{n}" for n in (1, 2, 3)]

	def stay(self, arrival=None, nights=2, confirmed=True):
		summary = hold(
			self.CODE,
			[stay_request(self.CODE, self.plan, self.guest, arrival or self.today, nights)],
			booking_details={"booking_source": "Phone Calls"},
		)
		name = summary["stays"][0]["name"]
		if confirmed:
			confirm(name)
		return frappe.get_doc("Stay Reservation", name)

	def in_house(self, room):
		stay = self.stay()
		assign_room(stay.name, room)
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def assignments(self, stay):
		return frappe.get_all(
			"Room Assignment",
			filters={"stay_reservation": stay.name},
			fields=["name", "hotel_room", "status", "previous_assignment", "move_reason"],
			order_by="creation asc",
		)

	def outage(self, room, start, end, state="Out of Order"):
		doc = frappe.get_doc(
			{
				"doctype": "Room State Period",
				"room": room,
				"state": state,
				"from_date": start,
				"to_date": end,
				"reason": "Leaking shower",
			}
		).insert()
		doc.submit()
		return doc


class TestBoard(TapeChartTestCase):
	def test_the_board_shows_rooms_bars_outages_and_unassigned_stays(self):
		placed = self.stay()
		assign_room(placed.name, f"{self.CODE}-101")
		waiting = self.stay(arrival=self.today + timedelta(days=1))
		held = self.stay(arrival=self.today + timedelta(days=2), confirmed=False)
		self.outage(f"{self.CODE}-103", self.today + timedelta(days=3), self.today + timedelta(days=5))

		data = tape_chart.board(self.CODE, start=self.today, days=7)
		self.assertEqual([row.name for row in data["rooms"]], self.rooms())
		self.assertEqual(len(data["days"]), 7)
		[bar] = data["bars"]
		self.assertEqual(
			(bar["stay"], bar["room"], bar["status"]), (placed.name, f"{self.CODE}-101", "Assigned")
		)
		self.assertTrue(bar["draggable"])
		unassigned = {row["stay"]: row for row in data["unassigned"]}
		self.assertEqual(set(unassigned), {waiting.name, held.name})
		self.assertTrue(unassigned[waiting.name]["draggable"])
		self.assertFalse(unassigned[held.name]["draggable"])  # a hold gets its room once confirmed
		[outage] = data["outages"]
		self.assertEqual((outage.room, outage.state), (f"{self.CODE}-103", "Out of Order"))

	def test_the_window_follows_settings_and_stays_within_bounds(self):
		frappe.db.set_single_value("Hospitality Settings", "tape_chart_days", 30)
		frappe.db.set_single_value("Hospitality Settings", "board_refresh_seconds", 5)
		data = tape_chart.board(self.CODE)
		self.assertEqual(len(data["days"]), 30)
		self.assertEqual(data["start"], self.today - timedelta(days=1))  # yesterday's departures show
		self.assertEqual(data["refresh_seconds"], 15)  # never faster than 15 seconds
		self.assertEqual(len(tape_chart.board(self.CODE, days=500)["days"]), 62)

	def test_a_move_shows_both_segments(self):
		stay = self.in_house(f"{self.CODE}-101")
		tape_chart.drop(stay.name, f"{self.CODE}-102", move_reason="Noise")
		bars = tape_chart.board(self.CODE, start=self.today, days=7)["bars"]
		self.assertEqual(
			{(bar["room"], bar["status"]) for bar in bars if bar["stay"] == stay.name},
			{(f"{self.CODE}-101", "Released"), (f"{self.CODE}-102", "Occupied")},
		)


class TestDragAndDrop(TapeChartTestCase):
	def test_dragging_a_confirmed_stay_to_another_room_assigns_it(self):
		stay = self.stay()
		assign_room(stay.name, f"{self.CODE}-101")
		check = tape_chart.check_drop(stay.name, f"{self.CODE}-102")
		self.assertEqual((check["allowed"], check["action"]), (True, "assign"))

		tape_chart.drop(stay.name, f"{self.CODE}-102")
		rows = self.assignments(stay)
		self.assertEqual(
			[(row.hotel_room, row.status) for row in rows],
			[(f"{self.CODE}-101", "Cancelled"), (f"{self.CODE}-102", "Assigned")],
		)

	def test_dragging_an_in_house_stay_moves_it_with_a_reason(self):
		stay = self.in_house(f"{self.CODE}-101")
		check = tape_chart.check_drop(stay.name, f"{self.CODE}-102")
		self.assertEqual((check["allowed"], check["action"], check["needs_reason"]), (True, "move", True))
		with self.assertRaises(DropRefusedError):
			tape_chart.drop(stay.name, f"{self.CODE}-102")

		tape_chart.drop(stay.name, f"{self.CODE}-102", move_reason="Noise")
		old, new = self.assignments(stay)
		self.assertEqual(
			(old.status, new.status, new.hotel_room), ("Released", "Occupied", f"{self.CODE}-102")
		)
		self.assertEqual((new.previous_assignment, new.move_reason), (old.name, "Noise"))

	def test_a_conflicting_drop_is_refused_and_nothing_changes(self):
		taken = self.stay()
		assign_room(taken.name, f"{self.CODE}-102")
		stay = self.stay()
		assign_room(stay.name, f"{self.CODE}-101")

		check = tape_chart.check_drop(stay.name, f"{self.CODE}-102")
		self.assertFalse(check["allowed"])
		self.assertIn(taken.name, check["reason"])
		with self.assertRaises(RoomUnavailableError):
			tape_chart.drop(stay.name, f"{self.CODE}-102")
		self.assertEqual(
			[(row.hotel_room, row.status) for row in self.assignments(stay)],
			[(f"{self.CODE}-101", "Assigned")],
		)

	def test_out_of_order_rooms_dirty_rooms_and_locks(self):
		stay = self.stay()
		self.outage(f"{self.CODE}-103", self.today, self.today + timedelta(days=1))
		self.assertIn("Out of Order", tape_chart.check_drop(stay.name, f"{self.CODE}-103")["reason"])

		frappe.db.set_value("Hotel Room", f"{self.CODE}-102", "housekeeping_condition", "Dirty")
		check = tape_chart.check_drop(stay.name, f"{self.CODE}-102")
		self.assertTrue(check["allowed"])  # a stay that hasn't arrived only gets a warning
		self.assertTrue(check["warnings"])
		guest = self.in_house(f"{self.CODE}-101")
		self.assertFalse(tape_chart.check_drop(guest.name, f"{self.CODE}-102")["allowed"])  # a move is now

		assign_room(stay.name, f"{self.CODE}-102", lock=True)
		set_room_lock(stay.name, True)
		self.assertIn("Do Not Move", tape_chart.check_drop(stay.name, None)["reason"])
		bar = next(
			bar for bar in tape_chart.board(self.CODE, start=self.today)["bars"] if bar["stay"] == stay.name
		)
		self.assertFalse(bar["draggable"])

	def test_dropping_on_the_unassigned_lane_takes_the_room_off(self):
		stay = self.stay()
		assign_room(stay.name, f"{self.CODE}-101")
		self.assertEqual(tape_chart.check_drop(stay.name, None)["action"], "unassign")
		tape_chart.drop(stay.name, None)
		self.assertEqual(self.assignments(stay)[0].status, "Cancelled")
		guest = self.in_house(f"{self.CODE}-102")
		self.assertFalse(tape_chart.check_drop(guest.name, None)["allowed"])

	def test_only_front_desk_roles_drop(self):
		stay = self.stay()
		frappe.set_user(make_user("hsp-tape-reservations@example.com", "Reservations Agent"))
		with self.assertRaises(frappe.PermissionError):
			tape_chart_api.drop_stay(stay.name, f"{self.CODE}-101")
		self.assertFalse(tape_chart_api.get_tape_chart(self.CODE)["can_move"])

	def test_readiness_follows_the_propertys_inspection_rule(self):
		"""A property that requires inspection doesn't take a guest into a room that is only Clean."""
		self.assertEqual(tape_chart.board(self.CODE)["ready_conditions"], ["Inspected", "Clean"])
		frappe.db.set_value("Hotel Property", self.CODE, "require_inspection", 1)
		# The board sends the rule, so its drag hint agrees with the server.
		self.assertEqual(tape_chart.board(self.CODE)["ready_conditions"], ["Inspected"])
		guest = self.in_house_inspected(f"{self.CODE}-101")
		check = tape_chart.check_drop(guest.name, f"{self.CODE}-102")
		self.assertFalse(check["allowed"])
		self.assertIn("not ready", check["reason"])
		frappe.db.set_value("Hotel Room", f"{self.CODE}-102", "housekeeping_condition", "Inspected")
		self.assertTrue(tape_chart.check_drop(guest.name, f"{self.CODE}-102")["allowed"])

		arriving = self.stay()
		warnings = tape_chart.check_drop(arriving.name, f"{self.CODE}-103")["warnings"]
		self.assertTrue(any("must be Inspected" in text for text in warnings))

	def in_house_inspected(self, room):
		frappe.db.set_value("Hotel Room", room, "housekeeping_condition", "Inspected")
		return self.in_house(room)

	def test_a_drop_respects_the_guests_preferences(self):
		"""The board ranks the room for the guest; a room missing a Required preference needs a
		reason, and the choice is logged as on the stay page."""
		frappe.db.set_single_value("Hospitality Settings", "enable_preference_room_ranking", 1)
		if not frappe.db.exists("Hotel Room Feature", "HSP Test Tape Step-free"):
			frappe.get_doc(
				{
					"doctype": "Hotel Room Feature",
					"feature_name": "HSP Test Tape Step-free",
					"category": "Accessibility",
				}
			).insert(ignore_permissions=True)
		room = frappe.get_doc("Hotel Room", f"{self.CODE}-101")
		room.set("features", [{"feature": "HSP Test Tape Step-free"}])
		room.save(ignore_permissions=True)
		preferences.add_preference(
			self.guest.name,
			"Accessibility",
			"Step-free access",
			priority="Required",
			room_feature="HSP Test Tape Step-free",
		)
		stay = self.stay()

		good = tape_chart.check_drop(stay.name, f"{self.CODE}-101")
		self.assertEqual((good["preference"]["rank"], good["needs_override"]), (1, False))
		bad = tape_chart.check_drop(stay.name, f"{self.CODE}-102")
		self.assertTrue(bad["needs_override"])
		self.assertEqual(bad["preference"]["required_missed"], ["Step-free access"])

		with self.assertRaises(room_ranking.PreferenceRequiredError):
			tape_chart.drop(stay.name, f"{self.CODE}-102")
		tape_chart.drop(stay.name, f"{self.CODE}-102", preference_override_reason="Guest asked for it")
		self.assertEqual(self.assignments(stay)[-1].hotel_room, f"{self.CODE}-102")
		feedback = frappe.get_value(
			"Guest Suggestion Feedback", {"stay_reservation": stay.name}, ["action", "reason"], as_dict=True
		)
		self.assertEqual((feedback.action, feedback.reason), ("Overridden", "Guest asked for it"))
