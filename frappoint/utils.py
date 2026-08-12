import frappe
from frappe.query_builder.functions import Max
from frappe.utils import add_days, date_diff, get_datetime, getdate, now_datetime

from .frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot import (
	generate_slots_for_specific_days,
)
from .frappoint.services.slot_cache_service import (
	purge_slot_cache_before_date,
)


def purge_old_slots():
	settings = frappe.get_cached_doc("Service Appointment Settings")
	today = getdate()

	if settings.allow_past_booking:
		purge_date = date_diff(today, settings.max_past_days)
	else:
		purge_date = today

	frappe.db.delete("Service Provider Appointment Slot", {"posting_date": ["<", purge_date]})
	purge_slot_cache_before_date(purge_date)

	frappe.db.commit()  # nosemgrep - scheduled cleanup commits after deleting old slots and cache rows.
	return f"Purged slots older than {purge_date}"


def replenish_slot_window():
	settings = frappe.get_cached_doc("Service Appointment Settings")
	today = getdate()
	window_end = add_days(today, settings.max_advance_days)

	active_shifts = frappe.get_all(
		"Service Provider Shift Assignment",
		filters={"status": "Active", "docstatus": 1},
		fields=["name", "start_date", "end_date"],
	)

	for shift in active_shifts:
		shift_start = max(today, shift.start_date)
		shift_end = min(shift.end_date or window_end, window_end)

		slot = frappe.qb.DocType("Service Provider Appointment Slot")
		result = (
			frappe.qb.from_(slot)
			.select(Max(slot.posting_date))
			.where(slot.shift_assignment == shift.name)
			.run()
		)
		last_slot_date = result[0][0] if result else None

		gen_start = add_days(last_slot_date, 1) if last_slot_date else shift_start

		if gen_start > shift_end:
			continue

		weekdays = get_shift_weekdays(shift.name)

		generate_slots_for_specific_days(
			shift_assignment=shift.name, weekdays=weekdays, start_date=gen_start, end_date=shift_end
		)


def expire_pending_payment_holds():
	"""Close unpaid draft appointments whose payment hold has expired and release reserved capacity."""
	from .frappoint.services.booking_transaction_service import (
		release_capacity_for_allocations,
		release_couple_appointment_allocations,
	)

	now = now_datetime()
	expired_appointments = frappe.get_all(
		"Service Appointment",
		filters={
			"status": ["in", ["Open", "Pending Payment"]],
			"payment_expires_at": ["<=", now],
			"docstatus": 0,
		},
		fields=["name", "booking_id", "couple_appointment_id"],
	)

	bookings_to_update = set()
	processed = set()
	expired_count = 0

	for candidate in expired_appointments:
		if candidate.name in processed:
			continue
		appointment_names = [candidate.name]
		if candidate.couple_appointment_id:
			appointment_names.append(candidate.couple_appointment_id)
		appointment_names = sorted(set(appointment_names))
		processed.update(appointment_names)
		savepoint = f"expire_hold_{candidate.name.replace('-', '_')}"
		frappe.db.savepoint(savepoint)
		try:
			if candidate.booking_id:
				frappe.db.sql(
					"SELECT name FROM `tabService Booking` WHERE name = %(name)s FOR UPDATE",
					{"name": candidate.booking_id},
				)
			frappe.db.sql(
				"""
				SELECT name FROM `tabService Appointment`
				WHERE name IN %(names)s ORDER BY name FOR UPDATE
				""",
				{"names": tuple(appointment_names)},
			)
			appointments = [frappe.get_doc("Service Appointment", name) for name in appointment_names]
			if len(appointments) == 2 and (
				appointments[0].couple_appointment_id != appointments[1].name
				or appointments[1].couple_appointment_id != appointments[0].name
			):
				frappe.throw("Couple appointment links must be reciprocal during hold expiry.")
			if any(
				row.docstatus != 0 or row.status not in {"Open", "Pending Payment"} for row in appointments
			):
				frappe.db.rollback(save_point=savepoint)
				continue
			if not any(
				row.payment_expires_at and get_datetime(row.payment_expires_at) <= now for row in appointments
			):
				frappe.db.rollback(save_point=savepoint)
				continue

			for appointment in appointments:
				appointment.recalculate_outstanding_from_payments()
				appointment.set_confirmation_targets()
			all_paid = all(
				appointment.get_paid_amount() >= appointment.confirmation_required_amount
				for appointment in appointments
			)
			if all_paid:
				primary = next(
					(
						row
						for row in appointments
						if not row.couple_appointment_id or row.is_primary_in_couple
					),
					appointments[0],
				)
				primary.confirm_appointment()
			else:
				if len(appointments) == 2:
					release_couple_appointment_allocations(
						appointment_names=[row.name for row in appointments],
						target_status="Released",
					)
				else:
					release_capacity_for_allocations(
						appointment_name=appointments[0].name,
						target_status="Released",
					)
				for appointment in appointments:
					appointment.db_set(
						{"status": "Closed", "payment_expires_at": None},
						update_modified=False,
					)
				expired_count += len(appointments)

			for appointment in appointments:
				if appointment.booking_id:
					bookings_to_update.add(appointment.booking_id)
			frappe.db.commit()  # nosemgrep - each hold group releases or confirms atomically.
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(
				frappe.get_traceback(),
				f"Failed to expire payment hold for {', '.join(appointment_names)}",
			)

	for booking_name in bookings_to_update:
		try:
			booking = frappe.get_doc("Service Booking", booking_name)
			booking.sync_financial_snapshot()
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Failed to recalculate booking {booking_name}")
	frappe.db.commit()  # nosemgrep - persist parent booking snapshots after grouped expiry.

	return f"Expired {expired_count} unpaid appointments"


def get_shift_weekdays(shift_assignment):
	"""
	Return weekday names expected by generate_slots_for_specific_days()
	Example: {"Monday", "Wednesday", "Friday"}
	"""

	sa = frappe.get_doc("Service Provider Shift Assignment", shift_assignment)

	DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

	# Daily shift all days
	if sa.repeat_type == "Daily":
		return set(DAYS)

	# Weekly shift checkbox-driven days
	if sa.repeat_type == "Weekly":
		day_fields = [
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		]

		selected_days = set()
		for idx, field in enumerate(day_fields):
			if sa.get(field):
				selected_days.add(DAYS[idx])

		return selected_days

	return set()


@frappe.whitelist()
def get_customer_contact_details(customer: str):
	primary_contact = frappe.db.get_value("Customer", customer, "customer_primary_contact")

	if primary_contact:
		return _get_contact_payload(primary_contact)

	linked_contacts = frappe.db.get_all(
		"Dynamic Link",
		filters={
			"link_doctype": "Customer",
			"link_name": customer,
			"parenttype": "Contact",
		},
		pluck="parent",
	)

	if linked_contacts:
		contact_name = frappe.db.get_value(
			"Contact",
			filters={
				"name": ["in", linked_contacts],
				"is_primary_contact": 1,
			},
			fieldname="name",
		)

		if contact_name:
			return _get_contact_payload(contact_name)

	contact_name = frappe.db.get_value(
		"Contact",
		filters={"name": ["in", linked_contacts]},
		fieldname="name",
		order_by="modified desc",
	)

	if contact_name:
		return _get_contact_payload(contact_name)

	return {}


def _get_contact_payload(contact_name):
	contact = frappe.get_doc("Contact", contact_name)
	contact.check_permission()

	return {
		"contact_person": contact.get("name"),
		"contact_display": contact.get("full_name"),
		"contact_email": contact.get("email_id"),
		"contact_mobile": contact.get("mobile_no"),
		"contact_phone": contact.get("phone"),
		"contact_designation": contact.get("designation"),
		"contact_department": contact.get("department"),
	}
