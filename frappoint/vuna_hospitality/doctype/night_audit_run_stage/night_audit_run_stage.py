# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class NightAuditRunStage(Document):
	"""One stage of a night audit run, with its counts and timings."""
