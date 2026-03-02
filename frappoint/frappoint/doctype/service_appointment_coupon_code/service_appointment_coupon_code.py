# Copyright (c) 2026, Navari LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ServiceAppointmentCouponCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappoint.frappoint.doctype.service_appointment_coupon_code_detail.service_appointment_coupon_code_detail import (
			ServiceAppointmentCouponCodeDetail,
		)

		applicable_for: DF.Literal[
			"Service Type", "Service Appointment", "Customer", "Customer Group", "Booking Source"
		]
		booking_source: DF.Literal["", "Portal", "Desk"]
		code: DF.Data | None
		coupon_type: DF.Literal["Promotional", "Complimentary", "Campaign"]
		customer: DF.Link | None
		customer_group: DF.Link | None
		disable: DF.Check
		discount_type: DF.Literal["Percentage", "Amount"]
		discount_value: DF.Float
		max_usage_count: DF.Int
		maximum_discount_amount: DF.Float
		minimum_order_value: DF.Float
		service_types: DF.Table[ServiceAppointmentCouponCodeDetail]
		times_used: DF.Int
		valid_from: DF.Date | None
		valid_till: DF.Date | None
	# end: auto-generated types

	def autoname(self):
		if not self.code:
			self.code = frappe.generate_hash(length=8).upper()

	def validate(self):
		self.validate_discount_value()
		self.validate_validity()

	def validate_validity(self):
		if self.valid_from and self.valid_till:
			if self.valid_from > self.valid_till:
				frappe.throw(_("Valid From cannot be greater than Valid Till"))

	def validate_discount_value(self):
		if self.discount_value <= 0:
			frappe.throw(_("Discount value must be greater than 0"))
		if self.discount_type == "Percentage" and self.discount_value > 100:
			frappe.throw(_("Percentage discount cannot exceed 100%"))

	def is_valid_for_appointment(self, appointment):
		if self.disable:
			return False, _("Coupon is not active")

		is_valid, msg = self.is_within_validity_period(appointment.appointment_date)
		if not is_valid:
			return False, msg

		if not self.applicable_for:
			return True, ""

		if self.applicable_for == "Customer":
			if self.customer != appointment.customer:
				return False, _("Coupon is not valid for this customer")
			return True, ""

		if self.applicable_for == "Customer Group":
			customer_group = frappe.get_cached_value("Customer", appointment.customer, "customer_group")
			if not customer_group or customer_group != self.customer_group:
				return False, _("Coupon is not valid for this customer")
			return True, ""

		if self.applicable_for == "Service Type":
			allowed_services = {d.service_type for d in self.service_types}
			if appointment.appointment_type not in allowed_services:
				return False, _("Coupon is not valid for this service")
			return True, ""

		if self.applicable_for == "Booking Source":
			if appointment.source != self.booking_source:
				return False, _("Coupon is not valid for this portal")
			return True, ""

	def is_usage_available(self):
		usage = self.get_usage_count()

		if self.max_usage_count and usage >= self.max_usage_count:
			return False, _("Coupon usage limit reached")
		return True, ""

	def is_min_order_met(self, order_amount):
		if self.minimum_order_value > 0:
			if order_amount < self.minimum_order_value:
				gap = self.minimum_order_value - order_amount
				return False, _("Add {0} more to use this coupon (min order {1})").format(
					gap, self.minimum_order_value
				)
		return True, ""

	def is_within_validity_period(self, appointment_date):
		appointment_date = getdate(appointment_date)

		valid_from = getdate(self.valid_from) if self.valid_from else None
		valid_till = getdate(self.valid_till) if self.valid_till else None

		if valid_from and appointment_date < valid_from:
			return False, _("Coupon is not yet active (starts {0})").format(self.valid_from)

		if valid_till and appointment_date > valid_till:
			return False, _("Coupon expired on {0}").format(self.valid_till)

		return True, ""

	def get_usage_count(self):
		return frappe.db.count("Service Appointment", {"coupon_code": self.name, "docstatus": 1})
