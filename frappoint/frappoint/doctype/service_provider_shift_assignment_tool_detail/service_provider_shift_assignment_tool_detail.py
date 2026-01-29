# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceProviderShiftAssignmentToolDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		service_provider: DF.Link
		service_provider_name: DF.Data | None
		service_unit: DF.Link | None
	# end: auto-generated types

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		pass

	def db_update(self):
		pass

	def delete(self):
		pass

	@staticmethod
	def get_list(args):
		pass

	@staticmethod
	def get_count(args):
		pass

	@staticmethod
	def get_stats(args):
		pass
