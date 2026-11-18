"""F15 Services (appointments) to folio."""

from datetime import datetime, time, timedelta
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, nowdate

from frappoint.frappoint.doctype.service_appointment.service_appointment import (
	ServiceAppointment,
	cancel_appointment,
)
from frappoint.vuna_hospitality.services import routing, service_charges, settlement
from frappoint.vuna_hospitality.services.front_desk import (
	add_stay_guest,
	assign_room,
	check_in,
	register_guest,
)
from frappoint.vuna_hospitality.services.money import to_minor
from frappoint.vuna_hospitality.services.service_charges import RoomChargedError, ServiceChargeError
from frappoint.vuna_hospitality.tests.test_folio import make_code, make_item, make_item_group, make_user
from frappoint.vuna_hospitality.tests.test_settlement import SettlementTestCase, make_company_customer
from frappoint.vuna_hospitality.tests.utils import hospitality_enabled

MASSAGE_ITEM = "HSP-TEST-DEEP-TISSUE"  # covered by the TMSG charge code
SERVICE = "HSP Test Deep Tissue"
PRICE = "60 Minutes"
RATE = 6000


def make_service_catalog(company: str, currency: str) -> str:
	"""A one-hour massage priced per booking, and a provider who gives it."""
	if not frappe.db.exists("Service Type", SERVICE):
		frappe.get_doc(
			{
				"doctype": "Service Type",
				"appointment_type": SERVICE,
				"item": MASSAGE_ITEM,
				"company": company,
				"default_duration_in_minutes": 60,
				"max_clients_per_slot": 4,
				"max_guests": 4,
				"prices": [
					{
						"price_name": PRICE,
						"currency": currency,
						"amount": RATE,
						"duration": 60,
						"pricing_model": "Per Booking",
					}
				],
			}
		).insert(ignore_permissions=True)
	provider = frappe.db.get_value("Service Provider", {"first_name": "HSP Test Therapist"}, "name")
	if not provider:
		provider = (
			frappe.get_doc(
				{
					"doctype": "Service Provider",
					"first_name": "HSP Test Therapist",
					"company": company,
					"active": 1,
					"services": [{"service_type": SERVICE, "default": 1}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	return provider


class ServiceTestCase(SettlementTestCase):
	CODE = "SVC"

	def setUp(self):
		super().setUp()
		# Charging to a room is a hospitality command: switch the module on for each test, so the
		# tests don't depend on the site's setting (CI's test site has it off).
		self._hospitality = hospitality_enabled(True)
		self._hospitality.__enter__()
		frappe.db.set_single_value("Hospitality Settings", "allow_room_charge_for_services", 1)
		frappe.db.set_single_value("Service Appointment Settings", "appointment_confirmation", 0)
		self.provider = make_service_catalog(self.prop.company, self.currency)
		self.customer = make_company_customer("HSP Test Spa Customer")
		self.day = getdate(add_days(nowdate(), 2))
		self.slot = 9
		self.primary = frappe.db.get_value(
			"Stay Guest", {"stay_reservation": self.stay.name, "role": "Primary"}, "name"
		)

	def tearDown(self):
		self._hospitality.__exit__(None, None, None)
		super().tearDown()

	# ------------------------------------------------------------------ fixtures

	def companion(self, stay=None, first_name="Amani", privileges="All"):
		stay = stay or self.stay
		profile = frappe.get_doc(
			{"doctype": "Guest Profile", "first_name": first_name, "last_name": f"Test{self.CODE}"}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Stay Reservation", stay.name, "adults", 1)
		with patch("frappoint.vuna_hospitality.services.front_desk._check_capacity"):
			guest = add_stay_guest(stay.name, profile.name)
		frappe.db.set_value("Stay Guest", guest, "charge_privileges", privileges)
		return guest

	def second_stay(self):
		stay = self.confirmed_stay(nights=2)
		assign_room(stay.name, f"{self.CODE}-102")
		for guest in frappe.get_all("Stay Guest", filters={"stay_reservation": stay.name}, pluck="name"):
			register_guest(guest)
		check_in(stay.name)
		return frappe.get_doc("Stay Reservation", stay.name)

	def booking(self, count=1, is_couple=0):
		return frappe.get_doc(
			{
				"doctype": "Service Booking",
				"customer": self.customer,
				"full_name": "Spa Guest",
				"booking_date": nowdate(),
				"status": "Draft",
				"is_couple": is_couple,
				"currency": self.currency,
				"items": [
					{
						"service_type": SERVICE,
						"pricing_model": "Per Booking",
						"qty": count,
						"rate": RATE,
						"total_amount": RATE * count,
						"currency": self.currency,
					}
				],
			}
		).insert(ignore_permissions=True)

	def appointment(self, booking, hour=None, guests=None):
		hour = hour if hour is not None else self.slot
		self.slot += 1
		doc = frappe.get_doc(
			{
				"doctype": "Service Appointment",
				"appointment_type": SERVICE,
				"appointment_price": PRICE,
				"appointment_date": self.day,
				"start_time": f"{hour:02d}:00:00",
				"end_time": f"{hour + 1:02d}:00:00",
				"appointment_provider": self.provider,
				"customer": self.customer,
				"company": self.prop.company,
				"booking_id": booking.name,
				"full_name": "Spa Guest",
				"status": "Open",
				"source": "Desk",
				"guests": [
					{"full_name": name, "is_primary": int(index == 0)}
					for index, name in enumerate(guests or ["Spa Guest"])
				],
			}
		)
		doc.flags.skip_calendar_event = True
		doc.flags.skip_resource_allocation = True
		doc.insert(ignore_permissions=True)
		return doc

	def couple(self, booking):
		first = self.appointment(booking, hour=15)
		second = self.appointment(booking, hour=15)
		frappe.db.set_value(
			"Service Appointment",
			first.name,
			{"couple_appointment_id": second.name, "is_primary_in_couple": 1},
		)
		frappe.db.set_value("Service Appointment", second.name, "couple_appointment_id", first.name)
		return first, second

	def charge(self, booking, plan, stay=None):
		"""plan: {appointment: [stay_guest, ...]} or {appointment: [{"stay_guest", ...}]}."""
		assignments = [
			{
				"appointment": appointment,
				"guests": [row if isinstance(row, dict) else {"stay_guest": row} for row in guests],
			}
			for appointment, guests in plan.items()
		]
		service_charges.link_booking(booking.name, (stay or self.stay).name, assignments)
		return service_charges.confirm_booking(booking.name)

	def complete(self, appointment_name):
		doc = frappe.get_doc("Service Appointment", appointment_name)
		doc.complete_and_invoice(str(doc.start_time), str(doc.end_time))
		return doc

	def participants(self, appointment_name):
		return frappe.get_all(
			"Service Participant",
			filters={"service_appointment": appointment_name},
			fields=[
				"name",
				"status",
				"stay_guest",
				"amount",
				"folio_transaction",
				"fee_transaction",
				"posted_folio",
				"posting_error",
				"role",
			],
			order_by="creation asc",
		)

	def service_lines(self, folio_name, appointment_name=None):
		filters = {"guest_folio": folio_name, "posting_key": ["like", "appt:%"]}
		if appointment_name:
			filters["source_name"] = appointment_name
		return frappe.get_all(
			"Folio Transaction",
			filters=filters,
			fields=[
				"name",
				"gross_amount",
				"consumer_guest_profile",
				"stay_guest",
				"posting_key",
				"direction",
				"accounting_mode",
				"reverses",
			],
			order_by="creation asc",
		)

	def use_fee_code(self):
		make_item_group("HSP Test Fees")
		make_item("HSP-TEST-POLICY-FEE", "HSP Test Fees")
		if not frappe.db.exists("Charge Code", "TFEE"):
			make_code("TFEE", item="HSP-TEST-POLICY-FEE")
		frappe.db.set_value("Hotel Property", self.CODE, "policy_fee_charge_code", "TFEE")

	def policy(self, policy_type, **values):
		return (
			frappe.get_doc(
				{
					"doctype": "Hotel Policy",
					"property": self.CODE,
					"policy_name": f"Spa {policy_type} {frappe.generate_hash(length=4)}",
					"policy_type": policy_type,
					"is_active": 1,
					**values,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)


class TestChargingToTheRoom(ServiceTestCase):
	def test_a_room_charged_booking_confirms_without_payment_and_refuses_desk_billing(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		self.assertGreater(appointment.confirmation_required_amount, 0)

		confirmed = self.charge(booking, {appointment.name: [self.primary]})
		self.assertEqual(confirmed, [appointment.name])
		appointment.reload()
		self.assertEqual((appointment.docstatus, appointment.status), (1, "Confirmed"))
		self.assertEqual(appointment.confirmation_required_amount, 0)
		booking.reload()
		self.assertEqual((booking.stay_reservation, booking.charge_to_room), (self.stay.name, 1))
		self.assertEqual(booking.status, "Confirmed")

		# No second revenue path: no services-side payment or invoice.
		payment = frappe.get_doc(
			{
				"doctype": "Service Appointment Payment",
				"reference_doctype": "Service Booking",
				"reference_docname": booking.name,
				"amount": RATE,
				"currency": self.currency,
				"mode_of_payment": "HSP Test Cash",
			}
		)
		with self.assertRaises(RoomChargedError):
			payment.insert(ignore_permissions=True)
		with self.assertRaises(RoomChargedError):
			booking.create_sales_invoice()
		with self.assertRaises(RoomChargedError):
			frappe.get_doc("Service Appointment", appointment.name).create_sales_invoice()

	def test_completion_posts_each_share_once_as_a_deferred_folio_charge(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		self.charge(booking, {appointment.name: [self.primary]})
		self.complete(appointment.name)

		[row] = self.participants(appointment.name)
		self.assertEqual(row.status, "Posted")
		[line] = self.service_lines(self.folio)
		self.assertEqual(line.name, row.folio_transaction)
		self.assertEqual(line.gross_amount, RATE)
		self.assertEqual(line.accounting_mode, "Deferred to Folio Invoice")
		self.assertEqual(line.posting_key, f"appt:{appointment.name}:{row.name}")
		self.assertEqual(line.stay_guest, self.primary)

		# Completing again, or a retry, posts nothing more.
		service_charges.post_appointment(appointment.name)
		self.assertEqual(len(self.service_lines(self.folio)), 1)
		# The services side created no invoice and no payment entry for it.
		self.assertFalse(frappe.db.exists("Sales Invoice", {"service_appointment": appointment.name}))

	def test_a_standalone_appointment_is_untouched(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		self.assertFalse(service_charges.is_room_charged("Service Appointment", appointment.name))
		self.assertGreater(appointment.confirmation_required_amount, 0)
		frappe.db.set_single_value(
			"Service Appointment Settings", "enable_appointment_confirmation_without_payment", 1
		)
		appointment.confirm_appointment()
		self.complete(appointment.name)
		self.assertEqual(self.participants(appointment.name), [])
		self.assertEqual(self.service_lines(self.folio), [])

	def test_linking_is_checked(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		blocked = self.companion(privileges="Room Charges")
		with self.assertRaises(ServiceChargeError):
			self.charge(booking, {appointment.name: [blocked]})
		with self.assertRaises(ServiceChargeError):
			service_charges.link_booking(booking.name, self.stay.name, [])  # who receives it?

		frappe.db.set_single_value("Hospitality Settings", "allow_room_charge_for_services", 0)
		with self.assertRaises(ServiceChargeError):
			self.charge(booking, {appointment.name: [self.primary]})
		frappe.db.set_single_value("Hospitality Settings", "allow_room_charge_for_services", 1)

		frappe.set_user(make_user("hsp-svc-housekeeper@example.com", "Housekeeping Attendant"))
		with self.assertRaises(frappe.PermissionError):
			self.charge(booking, {appointment.name: [self.primary]})

	def test_a_group_service_splits_the_price_and_keeps_every_unit(self):
		frappe.db.set_value("Service Type Price", {"parent": SERVICE}, "amount", 1001)
		booking = self.booking()
		appointment = self.appointment(booking, guests=["One", "Two", "Three"])
		guests = [self.primary, self.companion(first_name="Baraka"), self.companion(first_name="Chebet")]
		self.charge(booking, {appointment.name: guests})
		self.complete(appointment.name)

		rows = self.participants(appointment.name)
		self.assertEqual({row.role for row in rows}, {"Group Member"})
		lines = self.service_lines(self.folio)
		self.assertEqual(len(lines), 3)
		self.assertEqual(sum(to_minor(line.gross_amount, self.currency) for line in lines), 100100)
		self.assertEqual({line.stay_guest for line in lines}, set(guests))

	def test_taking_the_booking_back_to_desk_payment(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		service_charges.link_booking(
			booking.name,
			self.stay.name,
			[{"appointment": appointment.name, "guests": [{"stay_guest": self.primary}]}],
		)
		self.assertTrue(service_charges.is_room_charged("Service Appointment", appointment.name))
		with self.assertRaises(ServiceChargeError):
			service_charges.unlink_booking(booking.name, "")

		service_charges.unlink_booking(booking.name, "Guest pays at the spa")
		self.assertFalse(service_charges.is_room_charged("Service Booking", booking.name))
		self.assertGreater(
			frappe.db.get_value("Service Appointment", appointment.name, "confirmation_required_amount"), 0
		)
		self.assertEqual(self.participants(appointment.name)[0].status, "Not Charged")

	def test_a_stay_not_in_house_fails_the_posting_until_it_arrives(self):
		later = self.confirmed_stay(nights=2)
		guest = frappe.db.get_value("Stay Guest", {"stay_reservation": later.name, "role": "Primary"}, "name")
		booking = self.booking()
		appointment = self.appointment(booking)
		self.charge(booking, {appointment.name: [guest]}, stay=later)
		self.complete(appointment.name)

		[row] = self.participants(appointment.name)
		self.assertEqual(row.status, "Failed")
		self.assertIn("Confirmed", row.posting_error)
		self.assertEqual(frappe.db.get_value("Service Appointment", appointment.name, "status"), "Completed")

		assign_room(later.name, f"{self.CODE}-102")
		for name in frappe.get_all("Stay Guest", filters={"stay_reservation": later.name}, pluck="name"):
			register_guest(name)
		check_in(later.name)
		result = service_charges.retry_posting(appointment.name)
		self.assertEqual(len(result["posted"]), 1)
		self.assertEqual(self.participants(appointment.name)[0].status, "Posted")


class TestScenarios(ServiceTestCase):
	def test_couple_with_a_common_bill(self):
		"""Scenario 2: two guests share one room; each service is attributed to its consumer; one
		folio and one invoice settle the stay."""
		spouse = self.companion()
		booking = self.booking(count=2)
		mine, theirs = self.appointment(booking), self.appointment(booking)
		self.charge(booking, {mine.name: [self.primary], theirs.name: [spouse]})
		self.complete(mine.name)
		self.complete(theirs.name)

		lines = self.service_lines(self.folio)
		consumers = {line.stay_guest: line.consumer_guest_profile for line in lines}
		self.assertEqual(set(consumers), {self.primary, spouse})
		self.assertEqual(consumers[spouse], frappe.db.get_value("Stay Guest", spouse, "guest_profile"))

		self.check_out()
		result = self.settle_paid()
		invoice = frappe.get_doc("Sales Invoice", result["sales_invoice"])
		billed = frappe.get_all(
			"Folio Transaction",
			filters={"name": ["in", [line.name for line in lines]]},
			pluck="sales_invoice",
		)
		self.assertEqual(set(billed), {invoice.name})

	def test_corporate_guest_with_spouse(self):
		"""Scenario 4: the room goes to the company; the spouse's spa goes to her personal folio
		by a rule for her charges; the guest's own spa stays on his folio."""
		spouse = self.companion(first_name="Neema")
		company = make_company_customer("HSP Test Acme Ltd", 0, self.prop.company)
		company_folio = settlement.add_folio(self.stay.name, "Acme", payee_customer=company)
		spouse_profile = frappe.db.get_value("Stay Guest", spouse, "guest_profile")
		spouse_folio = settlement.add_folio(self.stay.name, "Neema", payee_guest_profile=spouse_profile)
		routing.add_rule(self.stay.name, company_folio, routing.ROOM_CHARGES)
		routing.add_rule(self.stay.name, spouse_folio, routing.ALL_CHARGES, stay_guest=spouse)

		booking = self.booking(count=2)
		his, hers = self.appointment(booking), self.appointment(booking)
		self.charge(booking, {his.name: [self.primary], hers.name: [spouse]})
		self.complete(his.name)
		self.complete(hers.name)

		self.assertEqual(len(self.service_lines(self.folio, his.name)), 1)
		self.assertEqual(len(self.service_lines(spouse_folio, hers.name)), 1)
		self.assertEqual(self.service_lines(company_folio), [])
		# The guest rule doesn't catch charges that aren't hers.
		self.assertEqual(routing.destination(self.stay.name, "TMSG"), self.folio)
		self.assertEqual(routing.destination(self.stay.name, "TMSG", stay_guest=spouse), spouse_folio)

		self.check_out()
		spouse_invoice = frappe.get_doc("Sales Invoice", self.settle_paid(spouse_folio)["sales_invoice"])
		self.assertEqual(
			spouse_invoice.customer, frappe.db.get_value("Guest Folio", spouse_folio, "payee_customer")
		)
		self.assertEqual(spouse_invoice.grand_total, RATE)

	def test_couple_service_for_hotel_guests(self):
		"""Scenario 8: a couple booking for two companions creates one participant each; charges
		route by consumer, and room sharing is not inferred (they stay in different rooms)."""
		other = self.second_stay()
		partner = frappe.db.get_value(
			"Stay Guest", {"stay_reservation": other.name, "role": "Primary"}, "name"
		)
		guests_before = {
			stay: frappe.db.count("Stay Guest", {"stay_reservation": stay})
			for stay in (self.stay.name, other.name)
		}
		booking = self.booking(count=2, is_couple=1)
		first, second = self.couple(booking)
		confirmed = self.charge(booking, {first.name: [self.primary], second.name: [partner]})
		self.assertEqual(set(confirmed), {first.name, second.name})
		self.complete(first.name)
		self.complete(second.name)

		[mine], [theirs] = self.participants(first.name), self.participants(second.name)
		self.assertEqual((mine.role, theirs.role), ("Couple Partner", "Couple Partner"))
		self.assertEqual(mine.posted_folio, self.folio)
		self.assertEqual(theirs.posted_folio, other.default_folio)
		self.assertEqual(
			guests_before,
			{stay: frappe.db.count("Stay Guest", {"stay_reservation": stay}) for stay in guests_before},
		)
		with self.assertRaises(ServiceChargeError):
			service_charges.link_booking(
				booking.name,
				self.stay.name,
				[
					{
						"appointment": first.name,
						"guests": [{"stay_guest": self.primary}, {"stay_guest": partner}],
					}
				],
			)

	def test_cancelled_service(self):
		"""Scenario 23: a cancellation follows the policy; nothing is fulfilled or issued from
		stock; the fee is its own traceable posting."""
		frappe.db.set_single_value("Service Appointment Settings", "auto_issue_consumables", 1)
		policy = self.policy(
			"Cancellation", free_until_hours_before_arrival=24, fee_type="Percentage of Stay", fee_value=50
		)
		frappe.db.set_value("Hotel Property", self.CODE, "service_cancellation_policy", policy)
		self.use_fee_code()

		early, late = self.booking(), self.booking()
		free = self.appointment(early)
		charged = self.appointment(late)
		self.charge(early, {free.name: [self.primary]})
		self.charge(late, {charged.name: [self.primary]})
		start = datetime.combine(self.day, time(self.slot - 1))

		with patch(
			"frappoint.vuna_hospitality.services.policies.local_now", return_value=start - timedelta(days=2)
		):
			cancel_appointment(free.name, allow_couple_single=True, commit=False)
		with patch(
			"frappoint.vuna_hospitality.services.policies.local_now", return_value=start - timedelta(hours=3)
		):
			cancel_appointment(charged.name, allow_couple_single=True, commit=False)

		[free_row], [late_row] = self.participants(free.name), self.participants(charged.name)
		self.assertEqual((free_row.status, free_row.fee_transaction), ("Cancelled", None))
		self.assertEqual(late_row.status, "Cancelled")
		self.assertIsNone(late_row.folio_transaction)
		[fee] = self.service_lines(self.folio)
		self.assertEqual(fee.name, late_row.fee_transaction)
		self.assertEqual(fee.gross_amount, RATE / 2)
		self.assertEqual(fee.posting_key, f"appt:{charged.name}:{late_row.name}:cancellation")
		for appointment in (free.name, charged.name):
			self.assertFalse(frappe.db.exists("Stock Entry", {"service_appointment": appointment}))

		# A manager waives it; the reversal keeps the trail.
		with self.assertRaises(frappe.PermissionError):
			frappe.set_user(make_user("hsp-svc-agent@example.com", "Front Desk Agent"))
			service_charges.waive_fee(late_row.name, "Goodwill")
		frappe.set_user("Administrator")
		service_charges.waive_fee(late_row.name, "Goodwill")
		self.assertTrue(frappe.db.exists("Folio Transaction", {"reverses": fee.name}))

	def test_a_missed_service_charges_the_no_show_fee(self):
		policy = self.policy("No-show", fee_type="Full Stay")
		frappe.db.set_value("Hotel Property", self.CODE, "service_no_show_policy", policy)
		self.use_fee_code()
		booking = self.booking()
		appointment = self.appointment(booking)
		self.charge(booking, {appointment.name: [self.primary]})

		doc = frappe.get_doc("Service Appointment", appointment.name)
		doc.status = "No Show"
		doc.save(ignore_permissions=True)
		[row] = self.participants(appointment.name)
		self.assertEqual(row.status, "No Show")
		self.assertEqual(frappe.db.get_value("Folio Transaction", row.fee_transaction, "gross_amount"), RATE)
		self.assertTrue(
			frappe.db.get_value("Folio Transaction", row.fee_transaction, "posting_key").endswith(":no-show")
		)


class TestBridgeIsolation(ServiceTestCase):
	def test_hooks_do_nothing_while_hospitality_is_off(self):
		booking = self.booking()
		appointment = self.appointment(booking)
		self.charge(booking, {appointment.name: [self.primary]})
		with hospitality_enabled(False):
			self.complete(appointment.name)
		self.assertEqual(self.participants(appointment.name)[0].status, "Pending")
		self.assertTrue(getattr(service_charges.on_appointment_update, "_hospitality_guarded", False))
		self.assertTrue(ServiceAppointment)
