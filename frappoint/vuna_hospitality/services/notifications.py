"""Messages to guests when something happens to their booking or stay (design §22.1; plan F20).

A **Guest Notification Rule** says when (booking confirmed, amended or cancelled; days before
arrival; check-in; hours before departure; check-out; a folio emailed; days after the stay), how
(email through the Email Queue, or SMS through SMS Settings), to whom (the primary guest, every
adult guest, the booker, or the payee), in which language, and for which stays.

- Each send is logged once in **Guest Notification Log**, keyed by (rule, booking or stay or
  folio, recipient, occurrence). Repeating an event never sends twice; a stay moved to new dates
  is a new occurrence for the time-based rules, so it gets its reminders again.
- Each message sent is also a **Communication** linked to the stay (or booking) and the guest's
  profile, so it shows on both timelines.
- Marketing rules go only to guests who agreed to marketing.
- A message carries the recipient's own name and the stay's details. A folio goes only to the
  folio's payee. No message carries another guest's folio or private details.
- Sending never fails the command that triggered it: commands queue it after they commit, and a
  failure is logged against the rule.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime

from frappoint.vuna_hospitality.services.feature_flag import hospitality_job

RULE = "Guest Notification Rule"
LOG = "Guest Notification Log"
STAY = "Stay Reservation"
BOOKING = "Hotel Booking"
FOLIO = "Guest Folio"
PROFILE = "Guest Profile"
SERVICE_FLAG = "from_notifications"

BOOKING_CONFIRMED = "Booking Confirmed"
BOOKING_AMENDED = "Booking Amended"
BOOKING_CANCELLED = "Booking Cancelled"
BEFORE_ARRIVAL = "Before Arrival"
CHECK_IN = "Check-in"
BEFORE_DEPARTURE = "Before Departure"
CHECK_OUT = "Check-out"
FOLIO_EMAILED = "Folio Emailed"
AFTER_STAY = "After Stay"
TIMED_EVENTS = (BEFORE_ARRIVAL, BEFORE_DEPARTURE, AFTER_STAY)

PRIMARY, ALL_ADULTS, BOOKER, PAYEE = "Primary Guest", "All Adult Guests", "Booker", "Payee"
EMAIL, SMS = "Email", "SMS"
SENT, FAILED, SKIPPED = "Sent", "Failed", "Skipped"
MARKETING = "Marketing"

ARRIVING = ("Confirmed", "Due In")
IN_HOUSE = ("In House", "Due Out")


class NotificationError(frappe.ValidationError):
	pass


# --------------------------------------------------------------------------- triggering


def notify(
	event: str,
	stay: str | None = None,
	booking: str | None = None,
	folio: str | None = None,
	occurrence: str | None = None,
) -> None:
	"""Queue the event's messages to go out once the current request commits."""
	property_name = _property_of(stay, booking, folio)
	if not property_name or not frappe.db.exists(
		RULE, {"property": property_name, "event": event, "enabled": 1}
	):
		return
	frappe.enqueue(
		"frappoint.vuna_hospitality.services.notifications.dispatch_queued",
		queue="short",
		enqueue_after_commit=True,
		now=frappe.in_test,
		notification_event=event,
		stay=stay,
		booking=booking,
		folio=folio,
		occurrence=occurrence,
	)


def _property_of(stay, booking, folio) -> str | None:
	if stay:
		return frappe.db.get_value(STAY, stay, "property")
	if folio:
		return frappe.db.get_value(FOLIO, folio, "property")
	if booking:
		return frappe.db.get_value(BOOKING, booking, "property")
	return None


def dispatch_queued(notification_event: str, **kwargs) -> list[str]:
	"""The queued job. (`event` is a keyword frappe.enqueue keeps for itself.)"""
	return dispatch(notification_event, **kwargs) or []


@hospitality_job
def dispatch(
	event: str,
	stay: str | None = None,
	booking: str | None = None,
	folio: str | None = None,
	occurrence: str | None = None,
	rule: str | None = None,
) -> list[str]:
	"""Send what every matching rule (or only `rule`) says for this event. Returns the logs written."""
	if folio and not stay:
		stay = frappe.db.get_value(FOLIO, folio, "stay_reservation")
	stay_row = _stay(stay) if stay else None
	booking = booking or (stay_row.hotel_booking if stay_row else None)
	booking_row = (
		frappe.db.get_value(
			BOOKING,
			booking,
			["name", "booking_source", "booker_guest_profile", "booker_customer", "booker_name"],
			as_dict=True,
		)
		if booking
		else None
	)
	property_name = _property_of(stay, booking, folio)
	logs = []
	only = rule
	for rule in _rules(property_name, event):
		if (only and rule.name != only) or not _matches(rule, stay_row, booking_row):
			continue
		for recipient in _pick_language(rule, _recipients(rule, stay_row, booking_row, folio), event):
			target = (
				(BOOKING, booking)
				if rule.recipient_role == BOOKER and booking
				else (STAY, stay)
				if stay
				else (FOLIO, folio)
			)
			key = ":".join(str(part) for part in (rule.name, target[1], recipient.key, occurrence or event))
			logs.append(_send(rule, event, key, recipient, stay_row, booking_row, folio))
	return [log for log in logs if log]


def _stay(stay: str) -> frappe._dict:
	return frappe.db.get_value(
		STAY,
		stay,
		[
			"name",
			"property",
			"hotel_booking",
			"lead_guest",
			"status",
			"arrival_date",
			"departure_date",
			"nights",
			"room_type",
			"rate_plan",
			"stay_type",
			"adults",
			"children",
			"eta",
			"default_folio",
		],
		as_dict=True,
	)


def _rules(property_name: str, event: str) -> list:
	return frappe.get_all(
		RULE,
		filters={"property": property_name, "event": event, "enabled": 1},
		fields=[
			"name",
			"rule_name",
			"event",
			"offset",
			"channel",
			"purpose",
			"recipient_role",
			"language",
			"email_template",
			"sms_message",
			"rate_plan",
			"booking_source",
			"vip_only",
			"stay_type",
		],
		order_by="creation asc",
	)


def _matches(rule, stay, booking) -> bool:
	if rule.rate_plan and (not stay or stay.rate_plan != rule.rate_plan):
		return False
	if rule.booking_source and (not booking or booking.booking_source != rule.booking_source):
		return False
	if rule.stay_type and (not stay or stay.stay_type != rule.stay_type):
		return False
	if rule.vip_only:
		lead = stay.lead_guest if stay else booking and booking.booker_guest_profile
		if not lead or not frappe.db.get_value(PROFILE, lead, "vip_level"):
			return False
	return True


# --------------------------------------------------------------------------- recipients


def _profile_recipient(profile: str) -> frappe._dict | None:
	row = frappe.db.get_value(
		PROFILE,
		profile,
		[
			"name",
			"first_name",
			"full_name",
			"email",
			"mobile_no",
			"language",
			"marketing_consent",
			"merged_into",
		],
		as_dict=True,
	)
	if not row or row.merged_into:
		return None
	return frappe._dict(
		key=row.name,
		guest_profile=row.name,
		first_name=row.first_name or row.full_name,
		full_name=row.full_name,
		email=row.email,
		mobile_no=row.mobile_no,
		language=row.language,
		consent=bool(row.marketing_consent),
	)


def _customer_recipient(customer: str) -> frappe._dict | None:
	row = frappe.db.get_value(
		"Customer", customer, ["name", "customer_name", "email_id", "mobile_no", "language"], as_dict=True
	)
	if not row:
		return None
	return frappe._dict(
		key=f"customer:{row.name}",
		guest_profile=None,
		first_name=row.customer_name,
		full_name=row.customer_name,
		email=row.email_id,
		mobile_no=row.mobile_no,
		language=row.language,
		consent=False,
	)


def _recipients(rule, stay, booking, folio) -> list:
	role = rule.recipient_role
	found = []
	if role == PRIMARY and stay and stay.lead_guest:
		found.append(_profile_recipient(stay.lead_guest))
	elif role == ALL_ADULTS and stay:
		for profile in frappe.get_all(
			"Stay Guest",
			filters={
				"stay_reservation": stay.name,
				"age_category": "Adult",
				"status": ["not in", ("Removed", "Did Not Stay")],
				"guest_profile": ["is", "set"],
			},
			pluck="guest_profile",
			order_by="creation asc",
		):
			found.append(_profile_recipient(profile))
	elif role == BOOKER and booking:
		if booking.booker_guest_profile:
			found.append(_profile_recipient(booking.booker_guest_profile))
		elif booking.booker_customer:
			found.append(_customer_recipient(booking.booker_customer))
	elif role == PAYEE:
		folio_name = folio or (stay.default_folio if stay else None)
		payee = (
			frappe.db.get_value(FOLIO, folio_name, ["payee_guest_profile", "payee_customer"], as_dict=True)
			if folio_name
			else None
		)
		if payee and payee.payee_guest_profile:
			found.append(_profile_recipient(payee.payee_guest_profile))
		elif payee and payee.payee_customer:
			found.append(_customer_recipient(payee.payee_customer))
	unique, seen = [], set()
	for row in found:
		if row and row.key not in seen:
			seen.add(row.key)
			unique.append(row)
	return unique


def _pick_language(rule, recipients: list, event: str) -> list:
	"""A rule in the guest's language wins over the property default (a rule with no language)."""
	if rule.language:
		return [row for row in recipients if row.language == rule.language]
	languages = set(
		frappe.get_all(
			RULE,
			filters={
				"property": frappe.db.get_value(RULE, rule.name, "property"),
				"event": event,
				"enabled": 1,
				"channel": rule.channel,
				"recipient_role": rule.recipient_role,
				"language": ["is", "set"],
			},
			pluck="language",
		)
	)
	return [row for row in recipients if not row.language or row.language not in languages]


# --------------------------------------------------------------------------- sending


def _log(values: dict) -> str:
	doc = frappe.get_doc({"doctype": LOG, **values})
	doc.flags[SERVICE_FLAG] = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _send(rule, event: str, key: str, recipient, stay, booking, folio) -> str | None:
	if frappe.db.exists(LOG, {"occurrence_key": key}):
		return None
	base = {
		"property": frappe.db.get_value(RULE, rule.name, "property"),
		"rule": rule.name,
		"event": event,
		"occurrence_key": key,
		"stay_reservation": stay.name if stay else None,
		"hotel_booking": booking.name if booking else None,
		"guest_folio": folio,
		"guest_profile": recipient.guest_profile,
		"channel": rule.channel,
		"sent_at": now_datetime(),
	}
	address = recipient.email if rule.channel == EMAIL else recipient.mobile_no
	reason = None
	if rule.purpose == MARKETING and not recipient.consent:
		reason = _("The guest hasn't agreed to marketing messages.")
	elif not address:
		reason = _("The guest has no {0} on file.").format(
			_("email address") if rule.channel == EMAIL else _("mobile number")
		)
	if reason:
		return _log({**base, "status": SKIPPED, "error": reason})

	savepoint = "guest_notification"
	frappe.db.savepoint(savepoint)
	try:
		context = message_context(recipient, stay, booking, folio)
		communication = _deliver(rule, address, context, recipient, stay, booking)
	except Exception as error:
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(
			title=f"Guest notification {rule.name}", reference_doctype=RULE, reference_name=rule.name
		)
		return _log(
			{**base, "status": FAILED, "recipient": address, "error": str(error) or error.__class__.__name__}
		)
	return _log({**base, "status": SENT, "recipient": address, "communication": communication})


def _deliver(rule, address: str, context: dict, recipient, stay, booking) -> str:
	reference = (STAY, stay.name) if stay else (BOOKING, booking.name)
	if rule.channel == EMAIL:
		template = frappe.get_doc("Email Template", rule.email_template)
		subject = frappe.render_template(
			template.subject, context
		)  # nosemgrep - templates are set up by managers
		body = frappe.render_template(  # nosemgrep - templates are set up by managers
			template.response_html if template.use_html else template.response, context
		)
		from frappe.core.doctype.communication.email import make

		name = make(
			recipients=[address],
			subject=subject,
			content=body,
			doctype=reference[0],
			name=reference[1],
			send_email=True,
			communication_medium="Email",
		)["name"]
	else:
		text = frappe.render_template(
			rule.sms_message, context
		)  # nosemgrep - templates are set up by managers
		from frappe.core.doctype.sms_settings.sms_settings import send_sms

		send_sms([address], text)
		comm = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "SMS",
				"sent_or_received": "Sent",
				"subject": text[:140],
				"content": text,
				"phone_no": address,
				"reference_doctype": reference[0],
				"reference_name": reference[1],
			}
		).insert(ignore_permissions=True)
		name = comm.name
	if recipient.guest_profile:
		comm = frappe.get_doc("Communication", name)
		comm.add_link(PROFILE, recipient.guest_profile)
		comm.save(ignore_permissions=True)
	return name


def message_context(recipient, stay, booking, folio) -> dict:
	"""What a template may use: the recipient's own name, the stay, the property, and a folio only
	when the recipient is that folio's payee."""
	property_name = stay.property if stay else frappe.db.get_value(BOOKING, booking.name, "property")
	prop = frappe.db.get_value(
		"Hotel Property",
		property_name,
		["property_name", "phone", "email", "address", "check_in_time", "check_out_time"],
		as_dict=True,
	)
	context = {
		"guest": {"first_name": recipient.first_name, "full_name": recipient.full_name},
		"booking": {"name": booking.name} if booking else {},
		"property": dict(prop or {}),
		"stay": {},
		"folio": None,
	}
	if stay:
		context["stay"] = {
			"name": stay.name,
			"arrival_date": frappe.format(stay.arrival_date, "Date"),
			"departure_date": frappe.format(stay.departure_date, "Date"),
			"nights": stay.nights,
			"adults": stay.adults,
			"children": stay.children,
			"eta": stay.eta,
			"room_type": frappe.db.get_value("Room Type", stay.room_type, "room_type_name"),
			"room_number": frappe.db.get_value(
				"Room Assignment",
				{"stay_reservation": stay.name, "status": ["in", ("Assigned", "Occupied", "Released")]},
				"room_number",
				order_by="start_datetime desc",
			),
		}
	if folio:
		row = frappe.db.get_value(
			FOLIO,
			folio,
			["name", "folio_label", "balance", "currency", "payee_guest_profile", "payee_customer"],
			as_dict=True,
		)
		is_payee = row and (
			(recipient.guest_profile and recipient.guest_profile == row.payee_guest_profile)
			or (recipient.key == f"customer:{row.payee_customer}")
		)
		if is_payee:
			context["folio"] = {
				"name": row.name,
				"label": row.folio_label,
				"balance": frappe.format(row.balance, {"fieldtype": "Currency", "options": row.currency}),
				"lines": [
					{
						"date": frappe.format(line.service_date or line.business_date, "Date"),
						"description": line.description_snapshot,
						"amount": frappe.format(
							line.gross_amount if line.direction == "Debit" else -line.gross_amount,
							{"fieldtype": "Currency", "options": row.currency},
						),
					}
					for line in frappe.get_all(
						"Folio Transaction",
						filters={"guest_folio": row.name, "docstatus": 1},
						fields=[
							"service_date",
							"business_date",
							"description_snapshot",
							"gross_amount",
							"direction",
						],
						order_by="posting_datetime asc",
					)
				],
			}
	return context


# --------------------------------------------------------------------------- folio email and timed rules


def email_folio(folio: str) -> list[str]:
	"""Send the folio to its payee by the property's Folio Emailed rules. Each request sends again."""
	property_name = frappe.db.get_value(FOLIO, folio, "property")
	if not property_name:
		raise frappe.DoesNotExistError(_("Guest Folio {0} does not exist.").format(folio))
	if not frappe.db.exists(RULE, {"property": property_name, "event": FOLIO_EMAILED, "enabled": 1}):
		frappe.throw(
			_("Set up a Folio Emailed notification rule for {0} first.").format(property_name),
			NotificationError,
		)
	logs = (
		dispatch(FOLIO_EMAILED, folio=folio, occurrence=f"{FOLIO_EMAILED}:{frappe.generate_hash(length=8)}")
		or []
	)
	from frappoint.vuna_hospitality.services.event_log import log_event

	log_event(FOLIO, folio, "Folio Emailed", data={"logs": logs})
	return logs


def due_timed(property_name: str, rule) -> list[tuple[str, str]]:
	"""(stay, occurrence) pairs a time-based rule is due for now."""
	business_date = getdate(frappe.db.get_value("Hotel Property", property_name, "business_date"))
	offset = cint(rule.offset)
	if rule.event == BEFORE_ARRIVAL:
		day = add_days(business_date, offset)
		stays = frappe.get_all(
			STAY,
			filters={"property": property_name, "status": ["in", ARRIVING], "arrival_date": day},
			pluck="name",
		)
		return [(stay, f"{BEFORE_ARRIVAL}:{day}") for stay in stays]
	if rule.event == AFTER_STAY:
		day = add_days(business_date, -offset)
		stays = frappe.get_all(
			STAY,
			filters={"property": property_name, "status": "Checked Out", "departure_date": day},
			pluck="name",
		)
		return [(stay, f"{AFTER_STAY}:{day}") for stay in stays]
	# Before Departure: within `offset` hours of the check-out time on the departure date.
	check_out = frappe.db.get_value("Hotel Property", property_name, "check_out_time") or "10:00:00"
	now = now_datetime()
	due = []
	for row in frappe.get_all(
		STAY,
		filters={
			"property": property_name,
			"status": ["in", IN_HOUSE],
			"departure_date": ["<=", add_days(now.date(), 1)],
		},
		fields=["name", "departure_date"],
	):
		leaving = get_datetime(f"{row.departure_date} {check_out}")
		if 0 <= (leaving - now).total_seconds() <= offset * 3600:
			due.append((row.name, f"{BEFORE_DEPARTURE}:{row.departure_date}"))
	return due


@hospitality_job
def send_timed() -> int:
	"""Hourly: reminders before arrival and departure, and follow-ups after the stay."""
	sent = 0
	for rule in frappe.get_all(
		RULE,
		filters={"enabled": 1, "event": ["in", TIMED_EVENTS]},
		fields=["name", "property", "event", "offset"],
	):
		for stay, occurrence in due_timed(rule.property, rule):
			sent += len(dispatch(rule.event, stay=stay, occurrence=occurrence, rule=rule.name) or [])
	return sent
