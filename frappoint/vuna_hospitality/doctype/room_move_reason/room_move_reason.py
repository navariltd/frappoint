# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RoomMoveReason(Document):
	"""Why a guest changed rooms: guest request, maintenance, upgrade, noise, and so on."""
