# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate

from frappoint.vuna_hospitality.services.guests import INVERSE_RELATIONSHIP


class GuestRelationship(Document):
	"""Links two guest profiles: "<related guest> is the <relationship> of <guest>"."""

	def validate(self):
		if self.guest_profile == self.related_guest:
			frappe.throw(_("A guest cannot be related to themselves."))
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be before Valid From."))
		self.validate_merged()
		self.validate_duplicate()

	def validate_merged(self):
		for guest in (self.guest_profile, self.related_guest):
			merged_into = frappe.db.get_value("Guest Profile", guest, "merged_into")
			if merged_into:
				frappe.throw(
					_("Guest Profile {0} was merged into {1}. Use that profile instead.").format(
						guest, merged_into
					)
				)

	def validate_duplicate(self):
		"""The same link, entered from either side, may exist only once while its dates overlap."""
		same_way = {
			"guest_profile": self.guest_profile,
			"related_guest": self.related_guest,
			"relationship_type": self.relationship_type,
		}
		other_way = {
			"guest_profile": self.related_guest,
			"related_guest": self.guest_profile,
			"relationship_type": INVERSE_RELATIONSHIP[self.relationship_type],
		}
		for filters in (same_way, other_way):
			for row in frappe.get_all(
				"Guest Relationship",
				filters={**filters, "name": ["!=", self.name or ""]},
				fields=["name", "valid_from", "valid_to"],
			):
				if self.overlaps(row):
					frappe.throw(
						_("This relationship is already recorded in {0}.").format(
							get_link_to_form("Guest Relationship", row.name)
						),
						frappe.DuplicateEntryError,
					)

	def overlaps(self, row) -> bool:
		start, end = (
			getdate(self.valid_from) if self.valid_from else None,
			getdate(self.valid_to) if self.valid_to else None,
		)
		other_start = getdate(row.valid_from) if row.valid_from else None
		other_end = getdate(row.valid_to) if row.valid_to else None
		return (not end or not other_start or other_start <= end) and (
			not other_end or not start or start <= other_end
		)
