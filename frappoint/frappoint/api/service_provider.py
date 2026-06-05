import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_providers_for_service(service_type, company=None):
	"""
	Get all providers who can deliver a specific service
	Use case: Provider selection on booking form
	"""

	_filters = {"service_type": service_type, "disabled": 0}

	providers = frappe.db.sql(
		"""
		SELECT DISTINCT
			sp.name,
			sp.provider_name,
			sp.gender,
			sp.designation,
			sp.color_code,
			sp.image,
			sps.default as is_default
		FROM `tabService Provider` sp
		INNER JOIN `tabService Provider Service` sps ON sps.parent = sp.name
		WHERE sps.service_type = %(service_type)s
		AND sps.disabled = 0
		AND sp.active = 1
		ORDER BY sps.default DESC, sp.provider_name
	""",
		{"service_type": service_type},
		as_dict=True,
	)

	return providers


@frappe.whitelist()
def get_provider_details(provider):
	"""
	Get detailed provider information
	Use case: Provider profile page
	"""
	doc = frappe.get_doc("Service Provider", provider)

	return {
		"name": doc.name,
		"provider_name": doc.provider_name,
		"first_name": doc.first_name,
		"middle_name_optional": doc.middle_name_optional,
		"last_name": doc.last_name,
		"email": doc.email,
		"mobile_no": doc.mobile_no,
		"designation": doc.designation,
		"color_code": doc.color_code,
		"active": doc.active,
		"services": [
			{"service_type": s.service_type, "default": s.default, "disabled": s.disabled}
			for s in doc.services
		],
	}
