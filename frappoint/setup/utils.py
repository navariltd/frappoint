import frappe
from erpnext.setup.utils import enable_all_roles_and_domains
from frappe.utils import now_datetime


def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = now_datetime().year
	if not frappe.get_list("Company"):
		# Keep these values in line with ERPNext's test bootstrap (erpnext.tests.utils.BootStrapTestData),
		# which runs when Frappe preloads test records linked to Company. It skips a record only if one with
		# the same fields already exists, so a different currency or company here (e.g. KES) makes it
		# insert "Standard Buying" a second time and fail with DuplicateEntryError. HRMS uses the same values.
		setup_complete(
			{
				"currency": "INR",
				"full_name": "Test User",
				"company_name": "_Test Company",
				"timezone": "Asia/Kolkata",
				"company_abbr": "_TC",
				"industry": "Manufacturing",
				"country": "India",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@navari.co.ke",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

	enable_all_roles_and_domains()
	frappe.db.commit()  # nosemgrep - setup routine persists created defaults before returning.
