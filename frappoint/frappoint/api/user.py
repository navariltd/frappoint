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
