# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_system_timezone, get_time

from frappoint.vuna_hospitality.services.rooms import normalize_code

ACCOUNT_FIELDS = (
	"guest_ledger_account",
	"advance_account",
	"room_post_clearing_account",
	"breakage_income_account",
	"cash_over_short_account",
)

# Set by night audit (F8) when it advances the business date.
BUSINESS_DATE_FLAG = "allow_business_date_change"


class HotelProperty(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		advance_account: DF.Link | None
		breakage_income_account: DF.Link | None
		business_date: DF.Date | None
		cash_over_short_account: DF.Link | None
		check_in_time: DF.Time
		check_out_time: DF.Time
		company: DF.Link
		currency: DF.Link | None
		day_use_end: DF.Time | None
		day_use_start: DF.Time | None
		default_cost_center: DF.Link | None
		email: DF.Data | None
		guest_ledger_account: DF.Link | None
		is_active: DF.Check
		night_audit_block_on_open_shifts: DF.Check
		phone: DF.Data | None
		policy_fee_charge_code: DF.Link | None
		post_stay_window_days: DF.Int
		property_code: DF.Data
		property_name: DF.Data
		room_post_clearing_account: DF.Link | None
		time_zone: DF.Autocomplete
		turnover_minutes: DF.Int
		walk_in_customer: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		# Runs before naming, so the code is clean before it becomes the record name.
		self.prepare()
		self.validate_time_zone()
		# The first business date is "today" where the hotel is.
		self.business_date = datetime.now(ZoneInfo(self.time_zone)).date()

	def before_validate(self):
		self.prepare()

	def prepare(self):
		self.property_code = normalize_code(self.property_code, "Property Code")
		if not self.time_zone:
			self.time_zone = get_system_timezone()

	def validate(self):
		self.validate_time_zone()
		self.validate_day_use_window()
		self.validate_accounts()
		self.validate_cost_center()
		self.validate_taxes_and_levies()
		self.validate_business_date_unchanged()

	def validate_time_zone(self):
		if self.time_zone not in available_timezones():
			frappe.throw(_("{0} is not a valid time zone.").format(self.time_zone))

	def validate_day_use_window(self):
		if (
			self.day_use_start
			and self.day_use_end
			and get_time(self.day_use_end) <= get_time(self.day_use_start)
		):
			frappe.throw(_("Day Use End must be later than Day Use Start."))

	def validate_accounts(self):
		for fieldname in ACCOUNT_FIELDS:
			account = self.get(fieldname)
			if account and frappe.db.get_value("Account", account, "company") != self.company:
				frappe.throw(
					_("{0} {1} does not belong to company {2}.").format(
						_(self.meta.get_label(fieldname)), account, self.company
					)
				)

	def validate_cost_center(self):
		if (
			self.default_cost_center
			and frappe.db.get_value("Cost Center", self.default_cost_center, "company") != self.company
		):
			frappe.throw(
				_("Cost Center {0} does not belong to company {1}.").format(
					self.default_cost_center, self.company
				)
			)

	def validate_taxes_and_levies(self):
		from frappoint.vuna_hospitality.services.pricing_masters import assert_fixed_revenue_code

		if (
			self.sales_taxes_template
			and frappe.db.get_value("Sales Taxes and Charges Template", self.sales_taxes_template, "company")
			!= self.company
		):
			frappe.throw(
				_("Sales Taxes and Charges Template {0} does not belong to company {1}.").format(
					self.sales_taxes_template, self.company
				)
			)
		if self.breakage_charge_code:
			assert_fixed_revenue_code(self.breakage_charge_code, _("Breakage Charge Code"))
		if self.policy_fee_charge_code:
			assert_fixed_revenue_code(self.policy_fee_charge_code, _("Policy Fee Charge Code"))
		seen = set()
		for levy in self.nightly_levies:
			assert_fixed_revenue_code(levy.charge_code, _("Nightly levy row {0}").format(levy.idx))
			if levy.amount <= 0:
				frappe.throw(_("Nightly levy row {0}: the amount must be more than zero.").format(levy.idx))
			if levy.charge_code in seen:
				frappe.throw(_("Nightly levy {0} is listed twice.").format(levy.charge_code))
			seen.add(levy.charge_code)

	def validate_business_date_unchanged(self):
		if self.is_new() or self.flags.get(BUSINESS_DATE_FLAG):
			return
		if self.has_value_changed("business_date"):
			frappe.throw(_("The business date can only be moved forward by night audit."))


@frappe.whitelist()
def get_time_zones() -> list[str]:
	"""Options for the Time Zone field."""
	return sorted(available_timezones())
