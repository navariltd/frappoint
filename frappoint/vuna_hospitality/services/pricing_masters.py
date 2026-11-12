"""Checks shared by the pricing masters (Occupancy Pricing Rule, Hotel Package, Hotel Property).

Night audit posts their charge codes on its own, with no one to pick an Item, so each code must be
an active Revenue code with a fixed Item. Checking that when the master is saved stops night audit
failing on a bad setup later.
"""

import frappe
from frappe import _

from frappoint.vuna_hospitality.doctype.charge_code.charge_code import is_in_group


def assert_fixed_revenue_code(charge_code: str | None, label: str) -> frappe._dict:
	"""`charge_code` must be an active Revenue code with a fixed Item. Returns the code's row."""
	if not charge_code:
		frappe.throw(_("{0} needs a charge code.").format(label))
	code = frappe.db.get_value(
		"Charge Code",
		charge_code,
		["name", "transaction_type", "is_active", "item", "item_group"],
		as_dict=True,
	)
	if not code or code.transaction_type != "Revenue" or not code.is_active or not code.item:
		frappe.throw(
			_("{0}: Charge Code {1} must be an active Revenue code with a fixed Item.").format(
				label, charge_code
			)
		)
	return code


def assert_allowance_covers(allowance_code: str | None, revenue_item: str, label: str) -> None:
	"""An allowance code must be an active Allowance code covering the component's own Item, so
	unused allowance can be credited back on that Item when it expires."""
	if not allowance_code:
		frappe.throw(_("{0} is an allowance and needs an Allowance Charge Code.").format(label))
	code = frappe.db.get_value(
		"Charge Code", allowance_code, ["transaction_type", "is_active", "item_group"], as_dict=True
	)
	if not code or code.transaction_type != "Allowance" or not code.is_active or not code.item_group:
		frappe.throw(
			_("{0}: Charge Code {1} must be an active Allowance code that covers an Item Group.").format(
				label, allowance_code
			)
		)
	item_group = frappe.db.get_value("Item", revenue_item, "item_group")
	if not is_in_group(item_group, code.item_group):
		frappe.throw(
			_(
				"{0}: Allowance Charge Code {1} covers {2}, which doesn't include the component's Item {3}."
			).format(label, allowance_code, code.item_group, revenue_item)
		)
