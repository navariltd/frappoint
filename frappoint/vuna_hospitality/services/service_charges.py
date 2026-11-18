"""Services (appointments) charged to a hotel stay's folio (design §12.2, §17.2, §18; feature F15).

A Service Booking made for hotel guests can be **charged to the room**. Each of its appointments
then gets one **Service Participant** per guest who receives it, linked to that guest's Stay Guest.
Nothing is paid or invoiced on the services side for such a booking:

- confirming it needs no payment (the confirmation amount is 0);
- Service Appointment Payments and Sales Invoices for it are refused (`assert_not_room_charged`),
  so the revenue is recognised once, by the folio's invoice at settlement (accounting mode
  "Deferred to Folio Invoice");
- completing an appointment posts each participant's share to a folio of that guest's stay, with
  the key `appt:<appointment>:<participant>`, so it posts once however often completion runs.
  The folio is the participant's own choice, else the stay's routing rules for that guest
  (services/routing.py), else the stay's default folio;
- cancelling it, or marking it a no-show, posts nothing for the service and no stock moves. A late
  cancellation or no-show fee from the property's service policies (snapshotted when the booking
  was linked) is a separate posting, `appt:<appointment>:<participant>:cancellation`.

A couple booking (`is_couple`) has two appointments, one per guest, so each gets one participant.
The guests can be on different stays: sharing a room is never inferred from the flag.

Standalone appointments are untouched: everything here starts from a booking linked to a stay.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, get_time, getdate, now_datetime

from frappoint.vuna_hospitality.constants import FOLIO_MANAGER_ROLES, SERVICE_CHARGE_ROLES
from frappoint.vuna_hospitality.services import folio
from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.feature_flag import assert_hospitality_enabled, hospitality_job
from frappoint.vuna_hospitality.services.money import from_minor, to_minor
from frappoint.vuna_hospitality.services.property_scope import assert_property_access
from frappoint.vuna_hospitality.services.reservations import STAY, _row

PARTICIPANT = "Service Participant"
APPOINTMENT = "Service Appointment"
BOOKING = "Service Booking"
SERVICE_FLAG = "from_service_charges"

PENDING = "Pending"
POSTED = "Posted"
CANCELLED = "Cancelled"
NO_SHOW = "No Show"
NOT_CHARGED = "Not Charged"
FAILED = "Failed"
OPEN_STATUSES = (PENDING, FAILED)

CONSUMER = "Consumer"
COUPLE_PARTNER = "Couple Partner"
GROUP_MEMBER = "Group Member"

# Stays a booking can be charged to, and stays a completed service posts to.
LINKABLE_STAY_STATUSES = ("Confirmed", "Due In", "In House", "Due Out")
CHARGEABLE_STAY_STATUSES = ("In House", "Due Out")
INELIGIBLE_GUEST_STATUSES = ("Checked Out", "Did Not Stay", "Removed")
# Appointments that no longer need a participant.
INACTIVE_APPOINTMENT_STATUSES = ("Cancelled", "Closed", "No Show", "Rescheduled")

CANCELLATION_EVENT = "Cancellation"
NO_SHOW_EVENT = "No-show"
EVENT_KEYS = {CANCELLATION_EVENT: "cancellation", NO_SHOW_EVENT: "no-show"}
POLICY_FIELDS = {
	CANCELLATION_EVENT: ("service_cancellation_policy", "cancellation_policy_snapshot"),
	NO_SHOW_EVENT: ("service_no_show_policy", "no_show_policy_snapshot"),
}
POLICY_SNAPSHOT_FIELDS = (
	"name",
	"policy_name",
	"policy_type",
	"free_until_hours_before_arrival",
	"fee_type",
	"fee_value",
	"guest_text",
)


class ServiceChargeError(frappe.ValidationError):
	pass


class RoomChargedError(ServiceChargeError):
	"""A payment or invoice was attempted for a booking whose services go to a folio."""


# --------------------------------------------------------------------------- the bridge


def is_room_charged(doctype: str, name: str | None) -> bool:
	"""Whether a Service Booking, or a Service Appointment's booking, is charged to a hotel stay.
	Cheap enough for the services code to call on every payment and confirmation."""
	if not name:
		return False
	booking = name if doctype == BOOKING else frappe.db.get_value(APPOINTMENT, name, "booking_id")
	return bool(booking and cint(frappe.db.get_value(BOOKING, booking, "charge_to_room")))


def assert_not_room_charged(doctype: str, name: str | None, action: str | None = None) -> None:
	"""Refuse a services-side payment or invoice for a room-charged booking (no double revenue)."""
	if not is_room_charged(doctype, name):
		return
	booking = name if doctype == BOOKING else frappe.db.get_value(APPOINTMENT, name, "booking_id")
	stay = frappe.db.get_value(BOOKING, booking, "stay_reservation")
	frappe.throw(
		_(
			"Booking {0} is charged to hotel stay {1}: its services are billed on the guest's folio. {2}"
		).format(booking, stay, action or _("Take it back to desk payment first.")),
		RoomChargedError,
		title=_("Charged to Room"),
	)


# --------------------------------------------------------------------------- linking


def room_charge_enabled() -> bool:
	from frappoint.vuna_hospitality.doctype.hospitality_settings.hospitality_settings import (
		is_hospitality_enabled,
	)

	return is_hospitality_enabled() and bool(
		cint(frappe.db.get_single_value("Hospitality Settings", "allow_room_charge_for_services"))
	)


def can_charge_to_room() -> bool:
	return room_charge_enabled() and bool(set(SERVICE_CHARGE_ROLES) & set(frappe.get_roles()))


def _assert_can_charge() -> None:
	assert_hospitality_enabled()
	if not room_charge_enabled():
		frappe.throw(
			_("Charging services to a room is switched off. Turn it on in Hospitality Settings."),
			ServiceChargeError,
		)
	frappe.only_for(SERVICE_CHARGE_ROLES)


def _stay(stay_name: str) -> frappe._dict:
	stay = _row(
		STAY,
		stay_name,
		["name", "property", "status", "hotel_booking", "currency", "default_folio", "lead_guest"],
	)
	if not stay:
		frappe.throw(_("Stay Reservation {0} does not exist.").format(stay_name), frappe.DoesNotExistError)
	assert_property_access(stay.property)
	return stay


def _booking(booking_name: str):
	if not frappe.db.exists(BOOKING, booking_name):
		frappe.throw(_("Service Booking {0} does not exist.").format(booking_name), frappe.DoesNotExistError)
	booking = frappe.get_doc(BOOKING, booking_name)
	if booking.docstatus == 2 or booking.status == "Cancelled":
		frappe.throw(_("Service Booking {0} is cancelled.").format(booking.name), ServiceChargeError)
	return booking


def _active_appointments(booking_name: str) -> list:
	return frappe.get_all(
		APPOINTMENT,
		filters={
			"booking_id": booking_name,
			"docstatus": ["!=", 2],
			"status": ["not in", INACTIVE_APPOINTMENT_STATUSES],
		},
		fields=[
			"name",
			"appointment_type",
			"appointment_date",
			"start_time",
			"status",
			"currency",
			"full_name",
			"couple_appointment_id",
		],
		order_by="creation asc",
	)


def _has_services_payment(booking_name: str, appointment_names: list[str]) -> bool:
	filters = [["docstatus", "=", 1]]
	if frappe.db.exists(
		"Service Appointment Payment",
		[*filters, ["reference_doctype", "=", BOOKING], ["reference_docname", "=", booking_name]],
	):
		return True
	return bool(
		appointment_names
		and frappe.db.exists(
			"Service Appointment Payment",
			[
				*filters,
				["reference_doctype", "=", APPOINTMENT],
				["reference_docname", "in", appointment_names],
			],
		)
	)


def _has_services_invoice(booking, appointment_names: list[str]) -> bool:
	if booking.get_linked_sales_invoice():
		return True
	meta = frappe.get_meta("Sales Invoice")
	return bool(
		appointment_names
		and meta.has_field("service_appointment")
		and frappe.db.exists(
			"Sales Invoice", {"service_appointment": ["in", appointment_names], "docstatus": ["!=", 2]}
		)
	)


def _eligible_guest(stay_guest: str, property_name: str) -> frappe._dict:
	guest = _row(
		folio.STAY_GUEST,
		stay_guest,
		[
			"name",
			"property",
			"stay_reservation",
			"guest_profile",
			"guest_name",
			"status",
			"role",
			"charge_privileges",
		],
	)
	if not guest:
		frappe.throw(_("Stay Guest {0} does not exist.").format(stay_guest), frappe.DoesNotExistError)
	if guest.property != property_name:
		frappe.throw(_("{0} is staying at another property.").format(guest.guest_name), ServiceChargeError)
	if guest.status in INELIGIBLE_GUEST_STATUSES:
		frappe.throw(
			_("{0} is {1} and can't charge services to the room.").format(
				guest.guest_name, _(guest.status).lower()
			),
			ServiceChargeError,
		)
	# The stay's primary guest always may; a companion needs "All" charge privileges.
	if guest.role != "Primary" and guest.charge_privileges != "All":
		frappe.throw(
			_(
				"{0} can't charge services to the room. Give them All charge privileges on the stay first."
			).format(guest.guest_name),
			ServiceChargeError,
		)
	stay = _row(STAY, guest.stay_reservation, ["name", "status"])
	if stay.status not in LINKABLE_STAY_STATUSES:
		frappe.throw(
			_("Stay {0} is {1}. Charge services to a confirmed or in-house stay.").format(
				stay.name, _(stay.status)
			),
			ServiceChargeError,
		)
	return guest


def _policy_snapshots(property_name: str) -> dict:
	values = {}
	for property_field, snapshot_field in POLICY_FIELDS.values():
		policy = frappe.db.get_value("Hotel Property", property_name, property_field)
		row = (
			frappe.db.get_value("Hotel Policy", policy, list(POLICY_SNAPSHOT_FIELDS), as_dict=True)
			if policy
			else None
		)
		values[snapshot_field] = frappe.as_json(row) if row else None
	return values


def _split(total_minor: int, shares: list[float]) -> list[int]:
	"""Split `total_minor` by percentage `shares`; the last share takes the rounding remainder."""
	amounts, given = [], 0
	for index, share in enumerate(shares):
		if index == len(shares) - 1:
			amounts.append(total_minor - given)
			break
		part = int(
			(Decimal(total_minor) * Decimal(str(share)) / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
		)
		amounts.append(part)
		given += part
	return amounts


def _shares(guests: list[dict]) -> list[float]:
	given = [row.get("share_percent") for row in guests]
	if all(value in (None, "", 0) for value in given):
		base = round(100 / len(guests), 4)
		return [base] * (len(guests) - 1) + [round(100 - base * (len(guests) - 1), 4)]
	shares = [flt(value) for value in given]
	if any(share <= 0 for share in shares) or abs(sum(shares) - 100) > 0.01:
		frappe.throw(_("Each guest's share must be more than 0 and the shares must add up to 100%."))
	return shares


def appointment_amount_minor(appointment) -> int:
	"""What the appointment costs after its own discount and its share of the booking's coupon."""
	doc = appointment if hasattr(appointment, "get_discount_amount_for_outstanding") else None
	doc = doc or frappe.get_doc(APPOINTMENT, appointment)
	net = max(0, flt(doc.total_amount) - flt(doc.get_discount_amount_for_outstanding()))
	return to_minor(net, doc.currency)


def link_booking(booking_name: str, stay_name: str, assignments: list[dict]) -> dict:
	"""Charge a Service Booking to hotel guests: one participant per guest per appointment.

	`assignments` is [{"appointment", "guests": [{"stay_guest", "share_percent"?, "target_folio"?}]}],
	one entry for each active appointment of the booking. Shares default to equal parts. Linking
	again replaces the participants, as long as nothing was charged yet.
	"""
	_assert_can_charge()
	booking = _booking(booking_name)
	stay = _stay(stay_name)
	if stay.status not in LINKABLE_STAY_STATUSES:
		frappe.throw(
			_("Stay {0} is {1}. Charge services to a confirmed or in-house stay.").format(
				stay.name, _(stay.status)
			),
			ServiceChargeError,
		)
	frappe.db.get_value(BOOKING, booking.name, "name", for_update=True)

	appointments = _active_appointments(booking.name)
	if not appointments:
		frappe.throw(_("Booking {0} has no appointments to charge.").format(booking.name), ServiceChargeError)
	by_name = {row.name: row for row in appointments}
	if any(row.status == "Completed" for row in appointments):
		frappe.throw(
			_("An appointment of this booking is already completed. Take its payment at the desk."),
			ServiceChargeError,
		)
	names = list(by_name)
	if _has_services_payment(booking.name, names):
		frappe.throw(
			_("Booking {0} already has a payment. Take the rest at the desk.").format(booking.name),
			ServiceChargeError,
		)
	if _has_services_invoice(booking, names):
		frappe.throw(_("Booking {0} is already invoiced.").format(booking.name), ServiceChargeError)
	if frappe.db.exists(
		PARTICIPANT,
		{"service_booking": booking.name, "status": ["in", (POSTED,)]},
	) or frappe.db.exists(PARTICIPANT, {"service_booking": booking.name, "fee_transaction": ["is", "set"]}):
		frappe.throw(
			_("Part of booking {0} is already charged to a folio.").format(booking.name), ServiceChargeError
		)

	plan = {}
	for entry in assignments or []:
		appointment = entry.get("appointment")
		if appointment not in by_name:
			frappe.throw(
				_("Appointment {0} isn't an active appointment of booking {1}.").format(
					appointment, booking.name
				),
				ServiceChargeError,
			)
		guests = [row for row in entry.get("guests") or [] if row.get("stay_guest")]
		if not guests:
			frappe.throw(_("Choose who receives {0}.").format(appointment), ServiceChargeError)
		if len({row["stay_guest"] for row in guests}) != len(guests):
			frappe.throw(_("A guest is listed twice on {0}.").format(appointment), ServiceChargeError)
		if by_name[appointment].couple_appointment_id and len(guests) != 1:
			frappe.throw(_("Each appointment of a couple booking is for one guest."), ServiceChargeError)
		plan[appointment] = guests
	missing = [name for name in names if name not in plan]
	if missing:
		frappe.throw(_("Choose who receives {0}.").format(", ".join(missing)), ServiceChargeError)

	snapshots = _policy_snapshots(stay.property)
	_clear_open_participants(booking.name)
	created = []
	for appointment_name, guests in plan.items():
		appointment = frappe.get_doc(APPOINTMENT, appointment_name)
		shares = _shares(guests)
		amounts = _split(appointment_amount_minor(appointment), shares)
		role = (
			COUPLE_PARTNER
			if appointment.couple_appointment_id or cint(booking.is_couple)
			else GROUP_MEMBER
			if len(guests) > 1
			else CONSUMER
		)
		for row, share, amount_minor in zip(guests, shares, amounts, strict=True):
			guest = _eligible_guest(row["stay_guest"], stay.property)
			target = (row.get("target_folio") or "").strip() or None
			if target:
				target_row = _row(folio.FOLIO, target, ["stay_reservation", "status"])
				if not target_row or target_row.stay_reservation != guest.stay_reservation:
					frappe.throw(
						_("Charge {0}'s services to a folio of their own stay.").format(guest.guest_name),
						ServiceChargeError,
					)
			doc = frappe.get_doc(
				{
					"doctype": PARTICIPANT,
					"property": stay.property,
					"service_appointment": appointment.name,
					"service_booking": booking.name,
					"service_type": appointment.appointment_type,
					"appointment_date": appointment.appointment_date,
					"start_time": appointment.start_time,
					"status": PENDING,
					"role": role,
					"stay_reservation": guest.stay_reservation,
					"stay_guest": guest.name,
					"guest_profile": guest.guest_profile,
					"guest_name": guest.guest_name,
					"delivery_room": folio._room_snapshot(guest.stay_reservation).room_number,
					"currency": appointment.currency,
					"share_percent": share,
					"amount": from_minor(amount_minor, appointment.currency),
					"target_folio": target,
					**snapshots,
				}
			)
			doc.flags[SERVICE_FLAG] = True
			doc.insert(ignore_permissions=True)
			created.append(doc.name)

	booking.db_set(
		{"stay_reservation": stay.name, "hotel_property": stay.property, "charge_to_room": 1},
		update_modified=False,
	)
	_refresh_confirmation_targets(booking.name)
	log_event(
		STAY,
		stay.name,
		"Services Charged to Room",
		data={"booking": booking.name, "participants": created},
		property_name=stay.property,
	)
	return booking_summary(booking.name)


def _clear_open_participants(booking_name: str) -> None:
	for name in frappe.get_all(PARTICIPANT, filters={"service_booking": booking_name}, pluck="name"):
		doc = frappe.get_doc(PARTICIPANT, name)
		doc.flags[SERVICE_FLAG] = True
		doc.delete(ignore_permissions=True)


def _refresh_confirmation_targets(booking_name: str) -> None:
	"""Recompute what the booking and its draft appointments need paid before confirmation."""
	booking = frappe.get_doc(BOOKING, booking_name)
	booking.sync_financial_snapshot()
	for name in frappe.get_all(
		APPOINTMENT, filters={"booking_id": booking_name, "docstatus": 0}, pluck="name"
	):
		appointment = frappe.get_doc(APPOINTMENT, name)
		appointment.set_confirmation_targets()
		appointment.db_set(
			"confirmation_required_amount", appointment.confirmation_required_amount, update_modified=False
		)


def unlink_booking(booking_name: str, reason: str) -> dict:
	"""Take a booking back to desk payment: its services are paid and invoiced on the services side
	again. Refused once anything was posted to a folio."""
	_assert_can_charge()
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for taking the booking back to desk payment."), ServiceChargeError)
	booking = _booking(booking_name)
	if not cint(booking.charge_to_room):
		return booking_summary(booking.name)
	_stay(booking.stay_reservation)
	if frappe.db.exists(PARTICIPANT, {"service_booking": booking.name, "status": POSTED}) or frappe.db.exists(
		PARTICIPANT, {"service_booking": booking.name, "fee_transaction": ["is", "set"]}
	):
		frappe.throw(
			_("Part of booking {0} is already on a folio. Reverse it there first.").format(booking.name),
			ServiceChargeError,
		)
	for name in frappe.get_all(
		PARTICIPANT,
		filters={"service_booking": booking.name, "status": ["in", OPEN_STATUSES]},
		pluck="name",
	):
		_set(name, status=NOT_CHARGED, notes=reason)
	booking.db_set("charge_to_room", 0, update_modified=False)
	_refresh_confirmation_targets(booking.name)
	log_event(
		STAY,
		booking.stay_reservation,
		"Services Returned to Desk Payment",
		reason=reason,
		data={"booking": booking.name},
		property_name=booking.hotel_property,
	)
	return booking_summary(booking.name)


def confirm_booking(booking_name: str) -> list[str]:
	"""Confirm a room-charged booking's draft appointments; no payment is needed."""
	if not is_room_charged(BOOKING, booking_name):
		frappe.throw(_("Booking {0} isn't charged to a room.").format(booking_name), ServiceChargeError)
	confirmed, done = [], set()
	for name in frappe.get_all(
		APPOINTMENT, filters={"booking_id": booking_name, "docstatus": 0}, pluck="name", order_by="creation"
	):
		if name in done:
			continue
		appointment = frappe.get_doc(APPOINTMENT, name)
		if appointment.status in ("Cancelled", "Closed"):
			continue
		if appointment.couple_appointment_id and not appointment.is_primary_in_couple:
			appointment = frappe.get_doc(APPOINTMENT, appointment.couple_appointment_id)
		appointment.confirm_appointment()
		for member in (appointment.name, appointment.couple_appointment_id):
			if member and member not in done:
				done.add(member)
				confirmed.append(member)
	frappe.get_doc(BOOKING, booking_name).sync_financial_snapshot()
	return confirmed


# --------------------------------------------------------------------------- posting


def _participants(appointment_name: str, statuses=OPEN_STATUSES) -> list:
	return frappe.get_all(
		PARTICIPANT,
		filters={"service_appointment": appointment_name, "status": ["in", statuses]},
		fields=[
			"name",
			"property",
			"stay_reservation",
			"stay_guest",
			"guest_name",
			"share_percent",
			"amount",
			"currency",
			"target_folio",
			"service_type",
			"cancellation_policy_snapshot",
			"no_show_policy_snapshot",
			"folio_transaction",
			"fee_transaction",
		],
		order_by="creation asc",
	)


def _set(name: str, **values) -> None:
	frappe.db.set_value(PARTICIPANT, name, values)


def _service_item(service_type: str) -> str:
	item = frappe.db.get_value("Service Type", service_type, "item")
	if not item:
		frappe.throw(
			_("Service Type {0} has no Item to charge it with.").format(service_type), ServiceChargeError
		)
	return item


def _target_folio(participant, charge_code: str) -> str:
	if participant.target_folio:
		status = frappe.db.get_value(folio.FOLIO, participant.target_folio, "status")
		if status in folio.POSTABLE_STATUSES:
			return participant.target_folio
	from frappoint.vuna_hospitality.services.routing import destination

	return destination(participant.stay_reservation, charge_code, stay_guest=participant.stay_guest)


def post_appointment(appointment_name: str) -> dict:
	"""Post each open participant's share of a completed appointment to their folio, once each.

	A participant that can't be posted (the stay has left, a folio is closed, no charge code covers
	the service) is marked Failed with the reason, so the others still post and staff can retry.
	"""
	appointment = frappe.get_doc(APPOINTMENT, appointment_name)
	if appointment.status != "Completed":
		frappe.throw(_("Appointment {0} isn't completed yet.").format(appointment.name), ServiceChargeError)
	participants = _participants(appointment.name)
	if not participants:
		return {"posted": [], "failed": []}
	total_minor = appointment_amount_minor(appointment)
	amounts = _split(total_minor, [flt(row.share_percent) for row in participants]) if total_minor else []
	posted, failed = [], []
	for row, amount_minor in zip(participants, amounts or [0] * len(participants), strict=True):
		savepoint = f"service_charge_{frappe.generate_hash(length=8)}"
		messages = len(frappe.local.message_log)
		frappe.db.savepoint(savepoint)
		try:
			result = _post_participant(appointment, row, amount_minor)
		except frappe.ValidationError as error:
			frappe.db.rollback(save_point=savepoint)
			del frappe.local.message_log[messages:]
			_set(row.name, status=FAILED, posting_error=str(error)[:500])
			failed.append({"participant": row.name, "error": str(error)})
			continue
		posted.append(result)
	return {"posted": posted, "failed": failed}


def _post_participant(appointment, row, amount_minor: int) -> dict:
	stay_status = frappe.db.get_value(STAY, row.stay_reservation, "status")
	if stay_status not in CHARGEABLE_STAY_STATUSES:
		frappe.throw(
			_("Stay {0} is {1}, so the service can't go on its folio. Take payment at the desk.").format(
				row.stay_reservation, _(stay_status)
			),
			ServiceChargeError,
		)
	amount = from_minor(amount_minor, appointment.currency)
	if amount_minor <= 0:
		_set(row.name, status=POSTED, amount=0, posted_on=now_datetime(), posting_error=None)
		return {"participant": row.name, "transaction": None, "amount": 0}
	item = _service_item(appointment.appointment_type)
	code = folio.resolve_charge_code(item)
	if code.accounting_mode != "Deferred to Folio Invoice":
		frappe.throw(
			_(
				"Charge Code {0} is accounted outside the folio, so a service charged to the room would be counted twice."
			).format(code.name),
			ServiceChargeError,
		)
	target = _target_folio(row, code.name)
	result = folio.post(
		target,
		code.name,
		amount,
		posting_key=f"appt:{appointment.name}:{row.name}",
		item=item,
		tax_inclusive=True,
		description=_("{0} for {1}").format(appointment.appointment_type, row.guest_name)[:140],
		service_date=appointment.appointment_date,
		source_doctype=APPOINTMENT,
		source_name=appointment.name,
		source_line=row.name,
		stay_guest=row.stay_guest,
	)
	_set(
		row.name,
		status=POSTED,
		amount=amount,
		posted_folio=target,
		folio_transaction=result["name"],
		posted_on=now_datetime(),
		posting_error=None,
	)
	if result["created"]:
		log_event(
			STAY,
			row.stay_reservation,
			"Service Charged",
			data={
				"appointment": appointment.name,
				"participant": row.name,
				"folio": target,
				"transaction": result["name"],
				"amount": amount,
			},
			property_name=row.property,
		)
	return {"participant": row.name, "transaction": result["name"], "amount": amount, "folio": target}


def retry_posting(appointment_name: str) -> dict:
	"""Post the participants that failed, after staff fixed the cause."""
	_assert_can_charge()
	property_name = frappe.db.get_value(PARTICIPANT, {"service_appointment": appointment_name}, "property")
	if not property_name:
		frappe.throw(
			_("Appointment {0} isn't charged to a room.").format(appointment_name), ServiceChargeError
		)
	assert_property_access(property_name)
	return post_appointment(appointment_name)


# --------------------------------------------------------------------------- cancellation and no-show


def appointment_start(appointment) -> datetime:
	return datetime.combine(getdate(appointment.appointment_date), get_time(appointment.start_time))


def fee_minor(row, event: str, appointment, at: datetime | None = None) -> tuple[int, dict | None]:
	"""The fee `event` costs this participant under the policy booked with it, and that policy."""
	snapshot = (
		row.cancellation_policy_snapshot if event == CANCELLATION_EVENT else row.no_show_policy_snapshot
	)
	policy = frappe._dict(frappe.parse_json(snapshot)) if snapshot else None
	if not policy or (policy.fee_type or "None") == "None":
		return 0, policy
	if event == CANCELLATION_EVENT and flt(policy.free_until_hours_before_arrival) > 0:
		from frappoint.vuna_hospitality.services.policies import local_now

		now = at or local_now(row.property)
		free_until = appointment_start(appointment) - timedelta(
			hours=flt(policy.free_until_hours_before_arrival)
		)
		if now < free_until:
			return 0, policy
	price_minor = to_minor(row.amount, row.currency)
	if policy.fee_type == "Fixed Amount":
		fee = Decimal(to_minor(policy.fee_value, row.currency)) * Decimal(str(flt(row.share_percent))) / 100
		return int(fee.quantize(Decimal(1), rounding=ROUND_HALF_UP)), policy
	if policy.fee_type == "Percentage of Stay":
		fee = Decimal(price_minor) * Decimal(str(flt(policy.fee_value))) / 100
		return int(fee.quantize(Decimal(1), rounding=ROUND_HALF_UP)), policy
	# First Night and Full Stay: a service has one "night", its price.
	return price_minor, policy


def close_appointment(appointment_name: str, event: str) -> list[dict]:
	"""The appointment was cancelled or missed: nothing is charged for the service, and each open
	participant gets the policy's fee, if any, as its own posting."""
	appointment = frappe.get_doc(APPOINTMENT, appointment_name)
	status = CANCELLED if event == CANCELLATION_EVENT else NO_SHOW
	fees = []
	for row in _participants(appointment.name):
		amount_minor, policy = fee_minor(row, event, appointment)
		values = {"status": status, "posting_error": None}
		if amount_minor > 0:
			result = _post_fee(appointment, row, event, amount_minor, policy)
			values.update(fee_transaction=result["name"], posted_folio=result["folio"])
			fees.append(result)
		_set(row.name, **values)
	_reverse_posted(appointment, event)
	return fees


def _post_fee(appointment, row, event: str, amount_minor: int, policy) -> dict:
	code = frappe.db.get_value("Hotel Property", row.property, "policy_fee_charge_code")
	if not code:
		frappe.throw(
			_(
				"The {0} policy charges a fee, but Hotel Property {1} has no Policy Fee Charge Code to post it with."
			).format(policy.policy_name, row.property),
			ServiceChargeError,
		)
	target = _target_folio(row, code)
	amount = from_minor(amount_minor, row.currency)
	result = folio.post(
		target,
		code,
		amount,
		posting_key=f"appt:{appointment.name}:{row.name}:{EVENT_KEYS[event]}",
		tax_inclusive=True,
		description=_("{0} fee: {1} for {2}").format(_(event), appointment.appointment_type, row.guest_name)[
			:140
		],
		service_date=appointment.appointment_date,
		# A cancelled appointment can't be linked, so the fee points at its participant.
		source_doctype=PARTICIPANT,
		source_name=row.name,
		source_line=appointment.name,
		stay_guest=row.stay_guest,
	)
	if result["created"]:
		log_event(
			STAY,
			row.stay_reservation,
			"Service Fee Posted",
			data={
				"appointment": appointment.name,
				"participant": row.name,
				"event": event,
				"policy": policy.name,
				"amount": amount,
				"transaction": result["name"],
			},
			property_name=row.property,
		)
	return {"name": result["name"], "folio": target, "amount": amount, "participant": row.name}


def _reverse_posted(appointment, event: str) -> None:
	"""A completed appointment cancelled afterwards (an amendment): reverse what it charged."""
	for row in _participants(appointment.name, statuses=(POSTED,)):
		if row.folio_transaction:
			folio.reverse_transaction(
				row.folio_transaction,
				_("Appointment {0}: {1}").format(appointment.name, _(event).lower()),
			)
		_set(row.name, status=CANCELLED if event == CANCELLATION_EVENT else NO_SHOW)


def waive_fee(participant: str, reason: str) -> dict:
	"""A Front Desk Manager reverses a service's cancellation or no-show fee, with a reason."""
	assert_hospitality_enabled()
	frappe.only_for(FOLIO_MANAGER_ROLES)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for waiving the fee."), ServiceChargeError)
	row = _row(PARTICIPANT, participant, ["name", "property", "stay_reservation", "fee_transaction"])
	if not row:
		frappe.throw(
			_("Service Participant {0} does not exist.").format(participant), frappe.DoesNotExistError
		)
	assert_property_access(row.property)
	if not row.fee_transaction:
		frappe.throw(_("{0} has no fee to waive.").format(participant), ServiceChargeError)
	result = folio.reverse_transaction(row.fee_transaction, reason)
	log_event(
		STAY,
		row.stay_reservation,
		"Service Fee Waived",
		reason=reason,
		data={"participant": row.name, "transaction": row.fee_transaction},
		property_name=row.property,
	)
	return result


# --------------------------------------------------------------------------- doc events


def _status_changed(doc) -> bool:
	before = doc.get_doc_before_save()
	return not before or before.status != doc.status


@hospitality_job
def on_appointment_update(doc, method=None):
	"""Service Appointment hook: completion posts, cancellation and no-show close participants."""
	cancelled = method == "on_cancel" or doc.status == "Cancelled"
	watched = (*OPEN_STATUSES, POSTED) if cancelled else OPEN_STATUSES
	if not frappe.db.exists(PARTICIPANT, {"service_appointment": doc.name, "status": ["in", watched]}):
		return
	if cancelled:
		close_appointment(doc.name, CANCELLATION_EVENT)
	elif doc.status == "No Show" and _status_changed(doc):
		close_appointment(doc.name, NO_SHOW_EVENT)
	elif doc.status == "Completed" and _status_changed(doc):
		post_appointment(doc.name)


@hospitality_job
def on_appointment_trash(doc, method=None):
	for name in frappe.get_all(PARTICIPANT, filters={"service_appointment": doc.name}, pluck="name"):
		if frappe.db.get_value(PARTICIPANT, name, "status") in (POSTED,) or frappe.db.get_value(
			PARTICIPANT, name, "fee_transaction"
		):
			frappe.throw(
				_("Appointment {0} is charged to a folio and can't be deleted.").format(doc.name),
				ServiceChargeError,
			)
		participant = frappe.get_doc(PARTICIPANT, name)
		participant.flags[SERVICE_FLAG] = True
		participant.delete(ignore_permissions=True)


# --------------------------------------------------------------------------- reading


PARTICIPANT_FIELDS = [
	"name",
	"service_appointment",
	"service_booking",
	"service_type",
	"appointment_date",
	"start_time",
	"status",
	"role",
	"stay_reservation",
	"stay_guest",
	"guest_name",
	"delivery_room",
	"share_percent",
	"amount",
	"currency",
	"target_folio",
	"posted_folio",
	"folio_transaction",
	"fee_transaction",
	"posting_error",
]


def _with_fees(rows: list) -> list:
	fees = {
		row.name: row.gross_amount
		for row in frappe.get_all(
			folio.TRANSACTION,
			filters={"name": ["in", [row.fee_transaction for row in rows if row.fee_transaction] or [""]]},
			fields=["name", "gross_amount"],
		)
	}
	reversed_fees = set(
		frappe.get_all(
			folio.TRANSACTION,
			filters={"reverses": ["in", list(fees) or [""]], "docstatus": 1},
			pluck="reverses",
		)
	)
	for row in rows:
		row["fee_amount"] = fees.get(row.fee_transaction) or 0
		row["fee_waived"] = row.fee_transaction in reversed_fees
	return rows


def booking_summary(booking_name: str) -> dict | None:
	"""The booking's hotel stay and participants, for the services desk."""
	values = frappe.db.get_value(
		BOOKING, booking_name, ["stay_reservation", "hotel_property", "charge_to_room"], as_dict=True
	)
	if not values or not values.stay_reservation:
		return None
	stay = frappe.db.get_value(
		STAY,
		values.stay_reservation,
		["name", "status", "arrival_date", "departure_date", "lead_guest"],
		as_dict=True,
	)
	participants = frappe.get_all(
		PARTICIPANT,
		filters={"service_booking": booking_name},
		fields=PARTICIPANT_FIELDS,
		order_by="creation asc",
	)
	return {
		"stay": values.stay_reservation,
		"property": values.hotel_property,
		"chargeToRoom": bool(values.charge_to_room),
		"stayStatus": stay.status if stay else None,
		"arrival": stay.arrival_date if stay else None,
		"departure": stay.departure_date if stay else None,
		"guestName": frappe.db.get_value("Guest Profile", stay.lead_guest, "full_name")
		if stay and stay.lead_guest
		else None,
		"room": folio._room_snapshot(values.stay_reservation).room_number,
		"participants": _with_fees(participants),
		"canUnlink": bool(values.charge_to_room)
		and not any(row.status == POSTED or row.fee_transaction for row in participants),
	}


def stay_services(stay_name: str) -> list:
	"""Services charged to this stay's guests, newest first, for the stay page."""
	rows = frappe.get_all(
		PARTICIPANT,
		filters={"stay_reservation": stay_name},
		fields=PARTICIPANT_FIELDS,
		order_by="appointment_date desc, start_time desc, creation asc",
	)
	return _with_fees(rows)


def stay_options(text: str = "", property_name: str | None = None, limit: int = 20) -> list[dict]:
	"""Confirmed and in-house stays whose guests can be charged, matching a name, room or stay."""
	from frappoint.vuna_hospitality.services.property_scope import scope_filters

	filters = scope_filters({"status": ["in", LINKABLE_STAY_STATUSES]})
	if property_name:
		assert_property_access(property_name)
		filters["property"] = property_name
	stays = frappe.get_all(
		STAY,
		filters=filters,
		fields=["name", "property", "status", "arrival_date", "departure_date", "lead_guest"],
		order_by="arrival_date asc",
		limit=500,
	)
	text = (text or "").strip().lower()
	results = []
	for stay in stays:
		guests = frappe.get_all(
			folio.STAY_GUEST,
			filters={"stay_reservation": stay.name, "status": ["not in", INELIGIBLE_GUEST_STATUSES]},
			fields=["name", "guest_name", "role", "charge_privileges", "guest_profile"],
			order_by="role asc, creation asc",
		)
		room = folio._room_snapshot(stay.name).room_number
		haystack = " ".join([stay.name, room or "", *[guest.guest_name or "" for guest in guests]]).lower()
		if text and text not in haystack:
			continue
		results.append(
			{
				"name": stay.name,
				"property": stay.property,
				"status": stay.status,
				"arrival": stay.arrival_date,
				"departure": stay.departure_date,
				"room": room,
				"guests": [
					{
						"name": guest.name,
						"guestName": guest.guest_name,
						"role": guest.role,
						"canCharge": guest.role == "Primary" or guest.charge_privileges == "All",
					}
					for guest in guests
				],
				"folios": frappe.get_all(
					folio.FOLIO,
					filters={"stay_reservation": stay.name, "status": ["in", folio.POSTABLE_STATUSES]},
					fields=["name", "folio_label", "is_default"],
					order_by="window_number asc",
				),
			}
		)
		if len(results) >= limit:
			break
	return results
