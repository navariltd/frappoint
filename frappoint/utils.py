import frappe
from frappe.utils import add_days, date_diff, getdate, now_datetime

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

	frappe.db.commit()
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

		last_slot_date = frappe.db.get_value(
			"Service Provider Appointment Slot",
			{"shift_assignment": shift.name},
			{"MAX": "posting_date"},
		)

		gen_start = add_days(last_slot_date, 1) if last_slot_date else shift_start

		if gen_start > shift_end:
			continue

		weekdays = get_shift_weekdays(shift.name)

		generate_slots_for_specific_days(
			shift_assignment=shift.name, weekdays=weekdays, start_date=gen_start, end_date=shift_end
		)


def expire_pending_payment_holds():
	"""Close unpaid draft appointments whose payment hold has expired and release reserved capacity."""
	from .frappoint.services.booking_transaction_service import release_capacity_for_allocations

	now = now_datetime()
	expired_appointments = frappe.get_all(
		"Service Appointment",
		filters={
			"status": ["in", ["Open", "Pending Payment"]],
			"payment_expires_at": ["<=", now],
			"docstatus": 0,
		},
		pluck="name",
	)

	bookings_to_update = set()

	for appointment_name in expired_appointments:
		try:
			appointment = frappe.get_doc("Service Appointment", appointment_name)
			appointment.recalculate_outstanding_from_payments()
			appointment.set_confirmation_targets()

			if appointment.get_paid_amount() >= appointment.confirmation_required_amount:
				appointment.update_payment_and_workflow_status()
				continue

			release_capacity_for_allocations(
				appointment_name=appointment.name,
				target_status="Expired",
			)
			appointment.db_set(
				{
					"status": "Closed",
					"payment_expires_at": None,
				},
				update_modified=False,
			)

			if appointment.booking_id:
				bookings_to_update.add(appointment.booking_id)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Failed to expire payment hold for {appointment_name}")

	for booking_name in bookings_to_update:
		try:
			booking = frappe.get_doc("Service Booking", booking_name)
			booking.sync_financial_snapshot()
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Failed to recalculate booking {booking_name}")

	return f"Expired {len(expired_appointments)} unpaid appointments"


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
def get_customer_contact_details(customer):
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
