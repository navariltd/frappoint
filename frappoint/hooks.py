app_name = "frappoint"
app_title = "Frappe Appointments"
app_publisher = "Navari LTD"
app_description = "Frappe Appointments"
app_email = "solutions@navari.co.ke"
app_license = "agpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext", "hrms"]

export_python_type_annotations = True

before_tests = "frappoint.setup.utils.before_tests"


# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "frappoint",
		"logo": "/assets/frappoint/images/logo_img.png",
		"title": "Frappoint",
		"route": "/app/frappoint",
		"has_permission": "frappoint.check_app_permission",
	}
]

website_route_rules = [
	{"from_route": "/frappoint/<path:app_path>", "to_route": "frappoint"},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/frappoint/css/frappoint.css"
# app_include_js = "/assets/frappoint/js/frappoint.js"

# include js, css files in header of web template
# web_include_css = "/assets/frappoint/css/frappoint.css"
# web_include_js = "/assets/frappoint/js/frappoint.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "frappoint/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "frappoint/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "frappoint.utils.jinja_methods",
# 	"filters": "frappoint.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "frappoint.install.before_install"
after_install = "frappoint.setup.setup.execute"

# Uninstallation
# ------------

# before_uninstall = "frappoint.uninstall.before_uninstall"
# after_uninstall = "frappoint.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "frappoint.utils.before_app_install"
# after_app_install = "frappoint.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "frappoint.utils.before_app_uninstall"
# after_app_uninstall = "frappoint.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "frappoint.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"frappoint.tasks.all"
# 	],
# 	"daily": [
# 		"frappoint.tasks.daily"
# 	],
# 	"hourly": [
# 		"frappoint.tasks.hourly"
# 	],
# 	"weekly": [
# 		"frappoint.tasks.weekly"
# 	],
# 	"monthly": [
# 		"frappoint.tasks.monthly"
# 	],
# }

# Testing
# -------

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "frappoint.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "frappoint.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["frappoint.utils.before_request"]
# after_request = ["frappoint.utils.after_request"]

# Job Events
# ----------
# before_job = ["frappoint.utils.before_job"]
# after_job = ["frappoint.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"frappoint.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
