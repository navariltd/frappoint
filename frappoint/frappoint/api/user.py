import frappe


@frappe.whitelist(allow_guest=False)
def get_user_details():
	if frappe.session.user == "Guest":
		return {}

	user = frappe.get_doc("User", frappe.session.user)
	return {
		"full_name": user.full_name,
		"email": user.email,
		"phone": user.phone,
	}


@frappe.whitelist(allow_guest=True)
def create_user(**kwargs):
	try:
		frappe.db.begin()

		if frappe.db.exists("User", kwargs.get("email")):
			return {"status": "failed", "message": "User already exists."}

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": kwargs.get("email"),
				"first_name": kwargs.get("first_name"),
				"last_name": kwargs.get("last_name"),
				"phone": kwargs.get("phone"),
				"new_password": kwargs.get("password"),
				"user_type": "System User",
				"enabled": 1,
			}
		)
		user.insert(ignore_permissions=True)
		frappe.db.commit()
		create_customer_from_user(user)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "User Creation Failed")
		frappe.throw(str(e))


def create_customer_from_user(user):
	if frappe.db.exists("Customer", user.email):
		return

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": user.full_name,
			"customer_type": "Individual",
			"customer_group": "All Customer Groups",
			"territory": "All Territories",
			"email_id": user.email,
		}
	)
	customer.insert(ignore_permissions=True)
	user.append("roles", {"role": "Customer"})
	user.save(ignore_permissions=True)
