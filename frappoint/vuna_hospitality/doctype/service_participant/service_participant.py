# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappoint.vuna_hospitality.services import service_charges


class ServiceParticipant(Document):
	"""One hotel guest receiving a service appointment, and where its charge goes (plan F15)."""

	def validate(self):
		if not self.flags.get(service_charges.SERVICE_FLAG):
			frappe.throw(
				_("Service participants change only by charging a booking to a room."),
				frappe.PermissionError,
			)

	def on_trash(self):
		if not self.flags.get(service_charges.SERVICE_FLAG):
			frappe.throw(_("Service participants are kept for the stay's history."))
