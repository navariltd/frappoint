import frappe
from frappe.utils.password import update_password


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
		update_password(user.name, kwargs.get("password"))

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
			"email_id": user.email,
		}
	)
	customer.insert(ignore_permissions=True)
	user.add_roles("Customer")
	user.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=False)
def update_user_profile(**kwargs):
	"""Update user profile information (name, phone)"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to update your profile")

	try:
		user = frappe.get_doc("User", frappe.session.user)

		# Update first name and last name
		if "first_name" in kwargs:
			user.first_name = kwargs.get("first_name")
		if "last_name" in kwargs:
			user.last_name = kwargs.get("last_name")

		# Update phone
		if "phone" in kwargs:
			user.phone = kwargs.get("phone")

		user.save(ignore_permissions=True)

		return {
			"status": "success",
			"message": "Profile updated successfully",
			"data": {
				"full_name": user.full_name,
				"email": user.email,
				"phone": user.phone,
			},
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "User Profile Update Failed")
		frappe.throw(f"Failed to update profile: {e!s}")


@frappe.whitelist(allow_guest=False)
def update_user_password(**kwargs):
	"""Update user password"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to update your password")

	current_password = kwargs.get("current_password")
	new_password = kwargs.get("new_password")
	confirm_password = kwargs.get("confirm_password")

	if not all([current_password, new_password, confirm_password]):
		frappe.throw("All password fields are required")

	if new_password != confirm_password:
		frappe.throw("New password and confirm password do not match")

	if not new_password or len(new_password) < 8:
		frappe.throw("Password must be at least 8 characters long")

	try:
		# Verify current password
		from frappe.utils.password import check_password

		check_password(frappe.session.user, current_password)

		# Update password
		update_password(frappe.session.user, new_password)

		return {"status": "success", "message": "Password updated successfully"}
	except frappe.AuthenticationError:
		frappe.throw("Current password is incorrect")
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Password Update Failed")
		frappe.throw(f"Failed to update password: {e!s}")


@frappe.whitelist(allow_guest=False)
def update_user_image(**kwargs):
	"""Update user profile image"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to update your profile image")

	file_url = kwargs.get("file_url")

	if not file_url:
		frappe.throw("File URL is required")

	try:
		user = frappe.get_doc("User", frappe.session.user)
		user.user_image = file_url
		user.save(ignore_permissions=True)

		return {
			"status": "success",
			"message": "Profile image updated successfully",
			"data": {"user_image": user.user_image},
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "User Image Update Failed")
		frappe.throw(f"Failed to update profile image: {e!s}")
