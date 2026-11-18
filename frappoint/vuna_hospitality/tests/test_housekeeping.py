"""F17 Housekeeping and maintenance."""

from datetime import timedelta

import frappe
from frappe.utils import add_days

from frappoint.vuna_hospitality.services import housekeeping, inventory, maintenance
from frappoint.vuna_hospitality.services.front_desk import (
	CheckInRefusedError,
	assign_room,
	check_in,
	check_out,
	install_default_move_reasons,
	move_room,
	register_guest,
)
from frappoint.vuna_hospitality.services.rooms import get_sellability
from frappoint.vuna_hospitality.tests.test_folio import FolioTestCase, make_user
from frappoint.vuna_hospitality.tests.test_reservations import counters

TASK = "Housekeeping Task"


def make_employee(first_name: str, company: str, user: str | None = None) -> str:
	name = frappe.db.get_value("Employee", {"first_name": first_name, "company": company}, "name")
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"last_name": "Test",
				"gender": "Female",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": company,
				"status": "Active",
				"user_id": user,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def put_on_shift(employee: str, company: str, on_date) -> None:
	if not frappe.db.exists("Shift Type", "HSP Test Morning"):
		frappe.get_doc(
			{
				"doctype": "Shift Type",
				"name": "HSP Test Morning",
				"__newname": "HSP Test Morning",
				"start_time": "07:00:00",
				"end_time": "15:00:00",
			}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"employee": employee,
			"company": company,
			"shift_type": "HSP Test Morning",
			"start_date": on_date,
			"end_date": on_date,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	doc.submit()


class HousekeepingTestCase(FolioTestCase):
	CODE = "HKP"

	def setUp(self):
		super().setUp()
		install_default_move_reasons()
		for room in (f"{self.CODE}-101", f"{self.CODE}-102"):
			frappe.db.set_value("Hotel Room", room, "housekeeping_condition", "Clean")

	def room(self, number="101"):
		return frappe.db.get_value(
			"Hotel Room",
			f"{self.CODE}-{number}",
			["housekeeping_condition", "occupancy_status", "sellability"],
			as_dict=True,
		)

	def tasks(self, number="101", **filters):
		return frappe.get_all(
			TASK,
			filters={"hotel_room": f"{self.CODE}-{number}", **filters},
			fields=["name", "task_type", "status", "source", "priority", "assigned_to", "stay_reservation"],
			order_by="creation asc",
		)

	def as_user(self, role, email=None):
		frappe.set_user(make_user(email or f"hsp-hk-{role.lower().replace(' ', '-')}@example.com", role))

	def arrival_in(self, number, nights=2):
		stay = self.confirmed_stay(nights=nights)
		assign_room(stay.name, f"{self.CODE}-{number}")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		return frappe.get_doc("Stay Reservation", stay.name)


class TestRoomTurnover(HousekeepingTestCase):
	def test_room_move_keeps_history_and_updates_housekeeping_for_both_rooms(self):
		"""Scenario 10: historical folio lines keep the original room; inventory and housekeeping
		update for both rooms."""
		stay = self.in_house_stay()
		before = self.massage(self.folio_of(stay))["name"]
		sold = counters(self.CODE, self.today)

		move_room(stay.name, f"{self.CODE}-102", "Noise")
		after = self.massage(self.folio_of(stay), request_id="after-move")["name"]
		self.assertEqual(frappe.db.get_value("Folio Transaction", before, "room_number_snapshot"), "101")
		self.assertEqual(frappe.db.get_value("Folio Transaction", after, "room_number_snapshot"), "102")
		self.assertEqual(counters(self.CODE, self.today), sold)  # same room type: nothing to give back

		old, new = self.room("101"), self.room("102")
		self.assertEqual((old.occupancy_status, old.housekeeping_condition), ("Vacant", "Dirty"))
		self.assertEqual(new.occupancy_status, "Occupied")
		[task] = self.tasks("101")
		self.assertEqual(
			(task.task_type, task.source, task.stay_reservation), ("Departure Clean", "Room Move", stay.name)
		)

	def test_check_out_asks_for_a_departure_clean_urgently_when_someone_arrives(self):
		stay = self.in_house_stay(nights=1)
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", add_days(self.today, 1))
		next_guest = self.confirmed_stay(nights=1, arrival=add_days(self.today, 1))
		assign_room(next_guest.name, f"{self.CODE}-101")
		check_out(stay.name, override_reason="Settles later")
		[task] = self.tasks("101")
		self.assertEqual(
			(task.task_type, task.source, task.priority), ("Departure Clean", "Check-out", "High")
		)

	def test_a_dirty_room_refuses_check_in_unless_a_manager_overrides(self):
		stay = self.arrival_in("101")
		frappe.db.set_value("Hotel Room", f"{self.CODE}-101", "housekeeping_condition", "Dirty")
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name)
		self.as_user("Front Desk Agent")
		with self.assertRaises(frappe.PermissionError):
			check_in(stay.name, override_reason="Guest is waiting")
		self.as_user("Front Desk Manager")
		check_in(stay.name, override_reason="Guest is waiting; room finished while they unpack")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Stay Reservation", stay.name, "status"), "In House")
		self.assertTrue(
			frappe.db.exists(
				"Hospitality Event Log",
				{"reference_name": stay.name, "event_type": "Checked In to Room Not Ready"},
			)
		)

	def test_clean_then_inspect_releases_the_room(self):
		frappe.db.set_value("Hotel Property", self.CODE, "require_inspection", 1)
		stay = self.arrival_in("101")
		frappe.db.set_value("Hotel Room", f"{self.CODE}-101", "housekeeping_condition", "Dirty")
		task = housekeeping.create_task(f"{self.CODE}-101", housekeeping.DEPARTURE_CLEAN)
		housekeeping.start(task)
		housekeeping.finish(task, room_found="Vacant")
		self.assertEqual(self.room().housekeeping_condition, "Clean")
		with self.assertRaises(CheckInRefusedError):
			check_in(stay.name)  # this property needs an inspection first

		with self.assertRaises(housekeeping.HousekeepingError):
			housekeeping.inspect(task, passed=False)  # say what needs redoing
		housekeeping.inspect(task, passed=False, notes="Bathroom mirror")
		self.assertEqual(frappe.db.get_value(TASK, task, "status"), "Open")
		self.assertEqual(self.room().housekeeping_condition, "Dirty")

		housekeeping.finish(task)
		housekeeping.inspect(task, passed=True)
		self.assertEqual(frappe.db.get_value(TASK, task, "status"), "Inspected")
		self.assertEqual(self.room().housekeeping_condition, "Inspected")
		check_in(stay.name)
		self.assertEqual(self.room().occupancy_status, "Occupied")


class TestTeam(HousekeepingTestCase):
	def test_attendants_work_on_their_own_tasks_and_supervisors_inspect(self):
		company = self.prop.company
		amina = make_employee(
			"Amina", company, make_user("hsp-hk-amina@example.com", "Housekeeping Attendant")
		)
		baraka = make_employee(
			"Baraka", company, make_user("hsp-hk-baraka@example.com", "Housekeeping Attendant")
		)
		mine = housekeeping.create_task(f"{self.CODE}-101", housekeeping.DEPARTURE_CLEAN, assigned_to=amina)
		free = housekeeping.create_task(f"{self.CODE}-102", housekeeping.TOUCH_UP)

		frappe.set_user("hsp-hk-baraka@example.com")
		with self.assertRaises(frappe.PermissionError):
			housekeeping.start(mine)
		housekeeping.start(free)  # an unassigned task is taken by whoever starts it
		self.assertEqual(frappe.db.get_value(TASK, free, "assigned_to"), baraka)
		housekeeping.finish(free)
		with self.assertRaises(frappe.PermissionError):
			housekeeping.inspect(free, passed=True)
		with self.assertRaises(frappe.PermissionError):
			housekeeping.assign(mine, baraka)

		frappe.set_user("hsp-hk-amina@example.com")
		housekeeping.start(mine)
		housekeeping.finish(mine, room_found="Vacant")

	def test_staff_on_shift_and_their_workload(self):
		company = self.prop.company
		on = make_employee("Chebet", company)
		off = make_employee("Daudi", company)
		put_on_shift(on, company, self.today)

		task = housekeeping.create_task(f"{self.CODE}-101", housekeeping.DEPARTURE_CLEAN)
		self.assertEqual(housekeeping.assign(task, on)["warnings"], [])
		other = housekeeping.create_task(f"{self.CODE}-102", housekeeping.STAYOVER)
		self.assertTrue(housekeeping.assign(other, off)["warnings"])  # allowed, with a warning

		people = {row["employee"]: row for row in housekeeping.staff(self.CODE)}
		self.assertTrue(people[on]["on_shift"])
		self.assertFalse(people[off]["on_shift"])
		self.assertEqual((people[on]["credits"], people[off]["credits"]), (1.0, 0.5))

	def test_stayovers_do_not_disturb_and_discrepancies(self):
		stay = self.in_house_stay()
		self.assertEqual(len(housekeeping.plan_stayovers(self.CODE)), 1)
		self.assertEqual(len(housekeeping.plan_stayovers(self.CODE)), 1)  # nothing added twice
		[task] = self.tasks("101", task_type="Stayover")

		housekeeping.mark_do_not_disturb(task.name)
		self.assertEqual(frappe.db.get_value(TASK, task.name, ["status", "do_not_disturb"]), ("Open", 1))
		self.assertEqual(housekeeping.discrepancies(self.CODE), [])

		housekeeping.finish(task.name, room_found="Vacant")
		[row] = housekeeping.discrepancies(self.CODE)
		self.assertEqual(
			(row["room_number"], row["front_desk"], row["housekeeping"]), ("101", "Occupied", "Vacant")
		)
		self.assertEqual(stay.status, "In House")


class TestMaintenance(HousekeepingTestCase):
	def available(self, night):
		inventory.ensure_rows([f"{self.CODE}-STD"], [night])
		return counters(self.CODE, night)[2]

	def test_out_of_order_needs_approval_then_leaves_inventory_until_resolved(self):
		tomorrow = add_days(self.today, 1)
		before = [self.available(self.today), self.available(tomorrow)]

		self.as_user("Housekeeping Attendant")
		request = maintenance.report(
			self.CODE,
			"Air conditioner leaking",
			room=f"{self.CODE}-102",
			severity="High",
			room_impact="Out of Order",
			back_in_service_on=add_days(self.today, 3),
		)
		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			maintenance.REQUEST, request, ["status", "room_state_period", "sla_due"], as_dict=True
		)
		self.assertEqual((row.status, row.room_state_period), ("Awaiting Approval", None))
		self.assertEqual(self.available(self.today), before[0])

		self.as_user("Housekeeping Attendant")
		with self.assertRaises(frappe.PermissionError):
			maintenance.approve(request)
		self.as_user("Maintenance Manager")
		maintenance.approve(request)
		period = frappe.db.get_value(maintenance.REQUEST, request, "room_state_period")
		self.assertEqual(
			frappe.db.get_value("Room State Period", period, ["docstatus", "state"]), (1, "Out of Order")
		)
		self.assertEqual([self.available(self.today), self.available(tomorrow)], [n - 1 for n in before])
		self.assertEqual(get_sellability(f"{self.CODE}-102", self.today), "Out of Order")

		# Fixed the next day: tonight's lost night stays lost; later nights come back.
		frappe.db.set_value("Hotel Property", self.CODE, "business_date", tomorrow)
		maintenance.start(request)
		maintenance.resolve(request, "Replaced the drain pipe")
		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			maintenance.REQUEST, request, ["status", "lost_room_nights", "room_state_period"], as_dict=True
		)
		self.assertEqual((row.status, row.lost_room_nights), ("Resolved", 1))
		self.assertEqual(frappe.db.get_value("Room State Period", row.room_state_period, "to_date"), tomorrow)
		self.assertEqual(self.available(tomorrow), before[1])
		self.assertEqual(self.room("102").housekeeping_condition, "Dirty")
		self.assertEqual(self.tasks("102", task_type="Touch-up")[0].priority, "High")

	def test_a_manager_takes_a_room_out_at_once_and_a_cancelled_request_gives_nights_back(self):
		later = add_days(self.today, 5)
		before = self.available(later)
		request = maintenance.report(
			self.CODE,
			"Repaint after water damage",
			room=f"{self.CODE}-101",
			severity="Low",
			room_impact="Out of Order",
			out_from=later,
			back_in_service_on=add_days(later, 2),
		)
		self.assertEqual(frappe.db.get_value(maintenance.REQUEST, request, "status"), "Open")
		self.assertEqual(self.available(later), before - 1)
		maintenance.cancel(request, "Booked with the wrong room")
		period = frappe.db.get_value(maintenance.REQUEST, request, "room_state_period")
		self.assertIsNone(period)
		self.assertEqual(self.available(later), before)

	def test_reporting_is_checked(self):
		with self.assertRaises(maintenance.MaintenanceError):
			maintenance.report(self.CODE, "  ")
		with self.assertRaises(maintenance.MaintenanceError):
			maintenance.report(self.CODE, "Broken lamp", room_impact="Out of Service")  # which room?
		with self.assertRaises(maintenance.MaintenanceError):
			maintenance.report(
				self.CODE,
				"Broken lamp",
				room=f"{self.CODE}-101",
				room_impact="Out of Service",
				out_from=self.today - timedelta(days=1),
			)
		self.as_user("Reservations Agent")
		with self.assertRaises(frappe.PermissionError):
			maintenance.report(self.CODE, "Broken lamp", room=f"{self.CODE}-101")

	def test_a_room_asset_opens_an_asset_repair(self):
		asset = frappe.db.get_value("Asset", {"docstatus": 1}, "name")
		if not asset:
			self.skipTest("No submitted Asset on this site.")
		frappe.db.set_value("Hotel Room", f"{self.CODE}-101", "asset", asset)
		request = maintenance.report(self.CODE, "Television dead", room=f"{self.CODE}-101")
		repair = frappe.db.get_value(maintenance.REQUEST, request, "asset_repair")
		self.assertEqual(
			frappe.db.get_value("Asset Repair", repair, ["asset", "repair_status"]), (asset, "Pending")
		)
