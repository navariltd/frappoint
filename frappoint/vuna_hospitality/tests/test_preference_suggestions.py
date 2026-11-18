"""F18 Preference suggestions and ranked room assignment."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from frappoint.vuna_hospitality.api import preferences as preference_api
from frappoint.vuna_hospitality.services import (
	guest_history,
	preferences,
	room_ranking,
	suggestions,
)
from frappoint.vuna_hospitality.services.front_desk import (
	assign_room,
	install_default_move_reasons,
)
from frappoint.vuna_hospitality.services.reservations import confirm, hold
from frappoint.vuna_hospitality.tests.test_folio import make_spa_catalog, make_user
from frappoint.vuna_hospitality.tests.test_reservations import make_booking_fixtures, stay_request
from frappoint.vuna_hospitality.tests.test_services_to_folio import SERVICE, make_service_catalog
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

STEP_FREE = "HSP Test Step-free Access"
QUIET = "HSP Test Quiet"
FEEDBACK = "Guest Suggestion Feedback"


def make_feature(name: str, category: str) -> str:
	if not frappe.db.exists("Hotel Room Feature", name):
		frappe.get_doc(
			{"doctype": "Hotel Room Feature", "feature_name": name, "category": category, "is_active": 1}
		).insert(ignore_permissions=True)
	return name


def make_guest(first_name: str, code: str, **fields) -> str:
	return (
		frappe.get_doc(
			{"doctype": "Guest Profile", "first_name": first_name, "last_name": f"Test{code}", **fields}
		)
		.insert(ignore_permissions=True)
		.name
	)


class PreferenceTestCase(IntegrationTestCase):
	CODE = "PRF"

	def setUp(self):
		frappe.db.savepoint("preference_test")
		self._hospitality = hospitality_enabled(True)
		self._hospitality.__enter__()
		self.prop, self.plan, guest = make_booking_fixtures(self.CODE, rooms=4)
		self.guest = guest.name
		self.today = getdate(self.prop.business_date)
		install_default_move_reasons()
		for fieldname, value in (
			("enable_preference_suggestions", 1),
			("suggestion_min_occurrences", 2),
			("enable_preference_room_ranking", 1),
		):
			frappe.db.set_single_value("Hospitality Settings", fieldname, value)
		make_feature(STEP_FREE, "Accessibility")
		make_feature(QUIET, "Noise")
		# 101: ground floor, step-free and quiet. 102: high floor, step-free.
		# 103: high floor, quiet, no step-free access. 104: ground floor, nothing.
		for number, floor, features in (
			("101", 1, (STEP_FREE, QUIET)),
			("102", 3, (STEP_FREE,)),
			("103", 3, (QUIET,)),
			("104", 1, ()),
		):
			room = frappe.get_doc("Hotel Room", self.room(number))
			room.floor = floor
			room.housekeeping_condition = "Clean"
			room.set("features", [{"feature": feature} for feature in features])
			room.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._hospitality.__exit__(None, None, None)
		frappe.db.rollback(save_point="preference_test")

	def room(self, number: str) -> str:
		return f"{self.CODE}-{number}"

	def stay(self, guest=None, arrival=None, nights=2):
		summary = hold(
			self.CODE,
			[
				stay_request(
					self.CODE,
					self.plan,
					frappe._dict(name=guest or self.guest),
					arrival or self.today,
					nights,
				)
			],
			booking_details={"booking_source": "Phone Calls"},
		)
		confirm(summary["stays"][0]["name"])
		return frappe.get_doc("Stay Reservation", summary["stays"][0]["name"])

	def past_stay(self, days_ahead: int, room: str | None = None, guest=None):
		"""A stay that is over. Built ahead of today, so it prices, then marked Checked Out."""
		stay = self.stay(guest=guest, arrival=self.today + timedelta(days=days_ahead))
		if room:
			assign_room(stay.name, self.room(room))
			frappe.db.set_value("Room Assignment", {"stay_reservation": stay.name}, "status", "Released")
		frappe.db.set_value("Stay Reservation", stay.name, "status", "Checked Out")
		frappe.db.set_value("Stay Guest", {"stay_reservation": stay.name}, "status", "Checked Out")
		return stay

	def prefer(self, value, priority="Normal", **fields):
		category = fields.pop(
			"category", "Accessibility" if fields.get("room_feature") == STEP_FREE else "Noise"
		)
		return preferences.add_preference(self.guest, category, value, priority=priority, **fields)


class TestRankedRoomAssignment(PreferenceTestCase):
	def scenario_preferences(self):
		self.prefer("High floor", "High", category="Floor")
		self.prefer("Quiet", "Normal", room_feature=QUIET)
		self.prefer("Step-free access", "Required", room_feature=STEP_FREE)

	def test_required_preference_removes_rooms_and_the_rest_rank_with_reasons(self):
		"""Scenario 39: rooms without step-free access are excluded; the rest are ranked with
		matched and missed preferences."""
		self.scenario_preferences()
		stay = self.stay()
		ranking = room_ranking.rank_rooms(stay.name)
		by_room = {row["room_number"]: row for row in ranking["rooms"]}

		self.assertEqual([row["room_number"] for row in ranking["rooms"] if row["eligible"]], ["102", "101"])
		self.assertEqual(ranking["top_room"], self.room("102"))
		self.assertEqual(by_room["102"]["rank"], 1)
		# Explanations list preferences by priority: Required, then High, then Normal.
		self.assertEqual(by_room["102"]["matched"], ["Step-free access", "High floor"])
		self.assertEqual(by_room["102"]["missed"], ["Quiet"])
		self.assertEqual(by_room["101"]["matched"], ["Step-free access", "Quiet"])
		self.assertEqual(by_room["101"]["missed"], ["High floor"])
		for number in ("103", "104"):
			self.assertFalse(by_room[number]["eligible"])
			self.assertEqual(by_room[number]["excluded"], ["No Step-free access"])
		self.assertFalse(ranking["no_room_meets_required"])

	def test_picking_the_second_room_is_logged_as_an_override(self):
		"""Scenario 39: staff pick the second-ranked room and the override is logged."""
		self.scenario_preferences()
		stay = self.stay()
		room_ranking.assign_ranked(stay.name, self.room("101"))

		feedback = frappe.get_all(
			FEEDBACK,
			filters={"stay_reservation": stay.name},
			fields=["action", "top_ranked_room", "chosen_room", "chosen_rank", "suggestion_type"],
		)
		self.assertEqual(len(feedback), 1)
		self.assertEqual(feedback[0].action, suggestions.OVERRIDDEN)
		self.assertEqual(feedback[0].top_ranked_room, self.room("102"))
		self.assertEqual(feedback[0].chosen_room, self.room("101"))
		self.assertEqual(feedback[0].chosen_rank, 2)
		self.assertEqual(feedback[0].suggestion_type, "Room")

	def test_picking_the_top_room_is_logged_as_such(self):
		self.scenario_preferences()
		stay = self.stay()
		room_ranking.assign_ranked(stay.name, self.room("102"))
		self.assertEqual(
			frappe.db.get_value(FEEDBACK, {"stay_reservation": stay.name}, "action"), suggestions.TOP_CHOSEN
		)

	def test_a_room_missing_a_required_preference_needs_a_reason(self):
		"""Scenario 39: with no room that meets it, staff must change something or override with a reason."""
		self.prefer("Step-free access", "Required", room_feature=STEP_FREE)
		for number in ("101", "102"):
			room = frappe.get_doc("Hotel Room", self.room(number))
			room.set("features", [])
			room.save(ignore_permissions=True)
		stay = self.stay()
		ranking = room_ranking.rank_rooms(stay.name)
		self.assertTrue(ranking["no_room_meets_required"])
		self.assertIsNone(ranking["top_room"])

		with self.assertRaises(room_ranking.PreferenceRequiredError):
			room_ranking.assign_ranked(stay.name, self.room("104"))
		room_ranking.assign_ranked(stay.name, self.room("104"), override_reason="Guest accepts the step")

		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "Confirmed")
		self.assertTrue(
			frappe.db.exists(
				"Room Assignment",
				{"stay_reservation": stay.name, "hotel_room": self.room("104"), "status": "Assigned"},
			)
		)
		feedback = frappe.get_value(
			FEEDBACK, {"stay_reservation": stay.name}, ["action", "reason"], as_dict=True
		)
		self.assertEqual(feedback.action, suggestions.OVERRIDDEN)
		self.assertEqual(feedback.reason, "Guest accepts the step")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": stay.name, "event_type": "Required Preference Overridden"},
			)
		)

	def test_a_stay_request_and_earlier_stays_rank_rooms_too(self):
		self.past_stay(10, room="104")
		self.past_stay(14, room="104")
		stay = self.stay()
		preferences.add_stay_request(stay.name, "Noise", "Quiet this time", room_feature=QUIET)
		by_room = {row["room_number"]: row for row in room_ranking.rank_rooms(stay.name)["rooms"]}

		self.assertEqual(by_room["104"]["matched"], ["Stayed here 2 times"])
		self.assertEqual(by_room["104"]["score"], 12)
		# 101 is quiet (the request, 10) and on the floor of both earlier stays (2 x 2).
		self.assertEqual(by_room["101"]["matched"], ["Quiet this time", "Same floor as before"])
		self.assertEqual(by_room["101"]["score"], 14)
		self.assertEqual((by_room["101"]["rank"], by_room["104"]["rank"]), (1, 2))

	def test_sensitive_preferences_rank_only_for_roles_that_see_them(self):
		self.prefer("Step-free access", "Required", room_feature=STEP_FREE, sensitivity="Sensitive")
		stay = self.stay()
		frappe.set_user(make_user("hsp-prf-agent@example.com", "Reservations Agent"))
		ranking = room_ranking.rank_rooms(stay.name)
		self.assertEqual(ranking["rules"], [])
		self.assertTrue(all(row["eligible"] for row in ranking["rooms"]))
		self.assertNotIn("Step-free access", str(ranking))

		frappe.set_user(make_user("hsp-prf-desk@example.com", "Front Desk Agent"))
		ranking = room_ranking.rank_rooms(stay.name)
		self.assertEqual([rule["label"] for rule in ranking["rules"]], ["Step-free access"])
		self.assertTrue(ranking["rules"][0]["sensitive"])

	def test_ranking_switched_off_keeps_room_number_order_and_logs_nothing(self):
		frappe.db.set_single_value("Hospitality Settings", "enable_preference_room_ranking", 0)
		self.prefer("Step-free access", "Required", room_feature=STEP_FREE)
		stay = self.stay()
		ranking = room_ranking.rank_rooms(stay.name)
		self.assertFalse(ranking["enabled"])
		self.assertEqual([row["room_number"] for row in ranking["rooms"]], ["101", "102", "103", "104"])
		room_ranking.assign_ranked(stay.name, self.room("104"))
		self.assertFalse(frappe.db.exists(FEEDBACK, {"stay_reservation": stay.name}))

	def test_a_room_preference_rooms_cannot_be_matched_to_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			preferences.add_preference(self.guest, "View", "Sea view")
		with self.assertRaises(frappe.ValidationError):
			preferences.add_preference(self.guest, "Dietary", "Vegetarian", priority="Required")
		# Saying it again reconfirms the same preference instead of adding another.
		first = self.prefer("Quiet", room_feature=QUIET)
		self.assertEqual(self.prefer("Quiet please", "High", room_feature=QUIET), first)
		self.assertEqual(frappe.db.get_value("Guest Preference", first, "priority"), "High")


class TestObservedSuggestions(PreferenceTestCase):
	def setUp(self):
		super().setUp()
		make_spa_catalog()
		currency = frappe.get_cached_value("Company", self.prop.company, "default_currency")
		make_service_catalog(self.prop.company, currency)

	def appointment(self, day, status="Completed", payment_status="Paid", guests=()):
		doc = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"appointment_type": SERVICE,
				"appointment_date": day,
				"status": status,
				"payment_status": payment_status,
				"company": self.prop.company,
			}
		)
		doc.name = f"HSP-PRF-{frappe.generate_hash(length=8)}"
		doc.db_insert()
		for index, guest in enumerate(guests, start=1):
			row = frappe.get_doc(
				{
					"doctype": "Service Appointment Guest",
					"parent": doc.name,
					"parenttype": "Service Appointment",
					"parentfield": "guests",
					"idx": index,
					**guest,
				}
			)
			row.name = frappe.generate_hash(length=10)
			row.db_insert()
		return doc.name

	def participant(self, appointment, stay, profile=None, status="Posted"):
		doc = frappe.get_doc(
			{
				"doctype": "Service Participant",
				"property": self.prop.name,
				"service_appointment": appointment,
				"service_type": SERVICE,
				"appointment_date": frappe.db.get_value(
					"Service Appointment", appointment, "appointment_date"
				),
				"status": status,
				"role": "Consumer",
				"stay_reservation": stay.name if stay else None,
				"guest_profile": profile or self.guest,
			}
		)
		doc.name = f"HSP-PRF-SVP-{frappe.generate_hash(length=8)}"
		doc.db_insert()
		return doc.name

	def massage_history(self):
		"""Four stays; a deep-tissue massage on three, plus a cancelled and a refunded one."""
		stays = [self.past_stay(days_ahead) for days_ahead in (3, 7, 11, 15)]
		for stay in stays[:3]:
			self.participant(self.appointment(stay.arrival_date), stay)
		self.participant(
			self.appointment(stays[3].arrival_date, status="Cancelled"), stays[3], status="Cancelled"
		)
		self.participant(self.appointment(stays[3].arrival_date, payment_status="Refunded"), stays[3])
		# The guest paid for a partner's massage: the partner consumed it, so it isn't theirs.
		partner = make_guest("Partner", self.CODE)
		self.participant(self.appointment(stays[3].arrival_date), stays[3], profile=partner)
		return stays

	def service_suggestion(self, data):
		return next(item for item in data["suggestions"] if item["type"] == "Service")

	def test_a_suggestion_counts_only_completed_services_the_guest_consumed(self):
		"""Scenario 38: "3 of the last 4 stays" with the last date; the cancelled and refunded
		massages and one the guest only paid for don't count."""
		stays = self.massage_history()
		item = self.service_suggestion(suggestions.guest_insights(self.guest))

		self.assertEqual(item["key"], f"service_type:{SERVICE}")
		self.assertEqual((item["in_stays"], item["of_stays"], item["visits"]), (3, 4, 0))
		self.assertEqual(item["last_date"], str(stays[2].arrival_date))
		self.assertTrue(item["evidence"].startswith("3 of the last 4 stays; last "))
		self.assertTrue(item["observed"])

	def test_dismissing_lowers_the_rank_and_keeps_the_history(self):
		"""Scenario 38: dismissing records feedback and ranks the suggestion lower next time."""
		self.massage_history()
		before = self.service_suggestion(suggestions.guest_insights(self.guest))
		suggestions.dismiss(self.guest, before["key"], before["evidence"])
		after = self.service_suggestion(suggestions.guest_insights(self.guest))

		self.assertLess(after["score"], before["score"])
		self.assertEqual(after["dismissed"], 1)
		self.assertEqual(after["in_stays"], 3)
		self.assertEqual(
			frappe.db.get_value(FEEDBACK, {"guest_profile": self.guest}, ["action", "evidence"]),
			(suggestions.DISMISSED, before["evidence"]),
		)

	def test_too_little_history_shows_nothing_and_a_new_guest_has_no_history(self):
		stay = self.past_stay(3)
		self.participant(self.appointment(stay.arrival_date), stay)
		data = suggestions.guest_insights(self.guest)
		self.assertEqual(data["suggestions"], [])
		self.assertFalse(data["no_history"])

		data = suggestions.guest_insights(make_guest("Newcomer", self.CODE))
		self.assertTrue(data["no_history"])
		self.assertEqual(data["suggestions"], [])

	def test_apply_to_stay_and_save_to_profile(self):
		"""Scenario 1: accepting a suggestion affects this stay only, unless "save to profile" is chosen."""
		self.massage_history()
		stay = self.stay()
		key = f"service_type:{SERVICE}"
		suggestions.apply_to_stay(stay.name, key, "3 of the last 4 stays")

		requests = preferences.stay_requests(stay.name)
		self.assertEqual(
			[(row.category, row.reference_name, row.source) for row in requests],
			[("Service Type", SERVICE, "Applied suggestion")],
		)
		self.assertFalse(frappe.db.exists("Guest Preference", {"guest_profile": self.guest}))
		data = suggestions.guest_insights(self.guest, stay.name)
		self.assertTrue(self.service_suggestion(data)["applied_to_stay"])

		suggestions.save_to_profile(self.guest, key, "3 of the last 4 stays", stay.name)
		data = suggestions.guest_insights(self.guest, stay.name)
		self.assertEqual(
			[(row.reference_name, row.source) for row in data["declared"]], [(SERVICE, "Accepted suggestion")]
		)
		# Declared now, so it is no longer offered as a suggestion.
		self.assertFalse([item for item in data["suggestions"] if item["type"] == "Service"])
		self.assertEqual(
			sorted(frappe.get_all(FEEDBACK, filters={"guest_profile": self.guest}, pluck="action")),
			[suggestions.APPLIED, suggestions.SAVED],
		)

	def test_a_room_suggestion_skips_rooms_the_guest_was_moved_out_of(self):
		first = self.past_stay(3, room="103")
		self.past_stay(7, room="103")
		# A third stay in 104, moved out of it for noise: 104 isn't suggested from that stay.
		noisy = self.past_stay(11, room="104")
		segment = frappe.db.get_value("Room Assignment", {"stay_reservation": noisy.name}, "name")
		moved = frappe.copy_doc(frappe.get_doc("Room Assignment", segment))
		moved.update({"hotel_room": self.room("101"), "previous_assignment": segment, "move_reason": "Noise"})
		moved.flags.ignore_validate = True
		moved.db_insert()
		self.past_stay(15, room="104")

		rooms = {
			item["title"]: item
			for item in suggestions.guest_insights(self.guest)["suggestions"]
			if item["type"] == "Room"
		}
		self.assertEqual(rooms["Room 103"]["in_stays"], 2)
		self.assertNotIn("Room 104", rooms)
		self.assertIn(first.name, rooms["Room 103"]["references"])

	def test_legacy_appointment_guests_count_once_a_match_is_confirmed(self):
		email = "hsp-prf-legacy@example.com"
		frappe.db.set_value("Guest Profile", self.guest, {"email": email, "mobile_no": "0712000111"})
		for day in (2, 5):
			self.appointment(
				self.today - timedelta(days=day), guests=[{"full_name": "Wanjiku", "email": email.upper()}]
			)
		# Two profiles share this phone: ambiguous, so it is never proposed.
		make_guest("Twin", self.CODE, mobile_no="0799000222")
		make_guest("Other", self.CODE, mobile_no="+254799000222")
		self.appointment(self.today, guests=[{"full_name": "Twin", "mobile_no": "0799 000 222"}])

		self.assertEqual(guest_history.propose_matches(), 2)
		# The site may hold other proposals; look only at this test's appointments.
		matches = [
			row for row in guest_history.proposed_matches() if row.service_appointment.startswith("HSP-PRF-")
		]
		self.assertEqual({row.guest_profile for row in matches}, {self.guest})
		self.assertEqual({row.match_basis for row in matches}, {"Email"})
		self.assertEqual(guest_history.propose_matches(), 0)
		self.assertEqual(suggestions.guest_insights(self.guest)["suggestions"], [])

		for match in matches:
			guest_history.review_match(match.name, confirm=True)
		item = self.service_suggestion(suggestions.guest_insights(self.guest))
		self.assertEqual((item["in_stays"], item["visits"]), (0, 2))
		self.assertTrue(item["evidence"].startswith("2 visits outside a stay"))

	def test_the_panel_endpoint_shows_declared_preferences_first(self):
		self.massage_history()
		stay = self.stay()
		self.prefer("Quiet", "High", room_feature=QUIET)
		data = preference_api.get_guest_insights(stay=stay.name)
		self.assertEqual([row.value for row in data["declared"]], ["Quiet"])
		self.assertEqual(self.service_suggestion(data)["in_stays"], 3)
		data = preference_api.apply_suggestion(stay.name, f"service_type:{SERVICE}")
		self.assertEqual(len(data["requests"]), 1)
