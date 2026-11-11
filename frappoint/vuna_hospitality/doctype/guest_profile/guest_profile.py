# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.utils.password import remove_encrypted_password

from frappoint.vuna_hospitality.services.event_log import log_event
from frappoint.vuna_hospitality.services.guests import (
	full_name,
	mask_document_number,
	normalize_email,
	normalize_phone,
)


class GuestProfile(Document):
	"""A person who books, stays, uses a service, or pays (design §30.15). Not the paying Customer."""

	def validate(self):
		self.first_name = (self.first_name or "").strip()
		self.last_name = (self.last_name or "").strip() or None
		self.preferred_name = (self.preferred_name or "").strip() or None
		self.full_name = full_name(self.first_name, self.last_name)
		self.email = normalize_email(self.email)
		self.mobile_no = normalize_phone(self.mobile_no)
		self.validate_merge()
		self.validate_user()
		self.update_id_hint()
		self.update_consent()
		self.validate_restriction()

	def validate_restriction(self):
		if not self.restriction_flag:
			self.restriction_reason = None
		elif not (self.restriction_reason or "").strip():
			frappe.throw(_("Give a reason for marking this guest Do Not Rent."))

	def validate_merge(self):
		if self.merged_into == self.name:
			frappe.throw(_("A guest profile cannot be merged into itself."))

	def validate_user(self):
		if not self.user:
			return
		other = frappe.db.get_value("Guest Profile", {"user": self.user, "name": ["!=", self.name]}, "name")
		if other:
			frappe.throw(_("User {0} is already linked to Guest Profile {1}.").format(self.user, other))

	def update_id_hint(self):
		number = self.id_document_number
		if not number:
			self.id_document_hint = None
		elif not set(number) <= {"*"}:
			# A newly typed number: Frappe encrypts it on save and stores only asterisks here.
			self.id_document_hint = mask_document_number(number)

	def update_consent(self):
		before = self.get_doc_before_save()
		previous = before.marketing_consent if before else 0
		if bool(self.marketing_consent) != bool(previous):
			self.consent_date = now_datetime()
			self.flags.consent_changed = True

	def on_update(self):
		if not self.id_document_number:
			remove_encrypted_password(self.doctype, self.name, "id_document_number")
		before = self.get_doc_before_save()
		if self.flags.consent_changed:
			log_event(
				self.doctype,
				self.name,
				"Consent Changed",
				reason=self.consent_source,
				data={"marketing_consent": bool(self.marketing_consent)},
			)
		if bool(self.restriction_flag) != bool(before.restriction_flag if before else 0):
			log_event(
				self.doctype,
				self.name,
				"Restriction Set" if self.restriction_flag else "Restriction Cleared",
				reason=self.restriction_reason,
			)
