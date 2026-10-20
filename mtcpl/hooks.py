app_name = "mtcpl"
app_title = "Mtcpl"
app_publisher = "Sudhanshu Badole"
app_description = "mtcpl"
app_email = "sudhanshubadole@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mtcpl",
# 		"logo": "/assets/mtcpl/logo.png",
# 		"title": "Mtcpl",
# 		"route": "/mtcpl",
# 		"has_permission": "mtcpl.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mtcpl/css/mtcpl.css"
# app_include_js = "/assets/mtcpl/js/mtcpl.js"

# include js, css files in header of web template
# web_include_css = "/assets/mtcpl/css/mtcpl.css"
# web_include_js = "/assets/mtcpl/js/mtcpl.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mtcpl/public/scss/website"

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
# app_include_icons = "mtcpl/public/icons.svg"

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
# 	"methods": "mtcpl.utils.jinja_methods",
# 	"filters": "mtcpl.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mtcpl.install.before_install"
# after_install = "mtcpl.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mtcpl.uninstall.before_uninstall"
# after_uninstall = "mtcpl.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mtcpl.utils.before_app_install"
# after_app_install = "mtcpl.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mtcpl.utils.before_app_uninstall"
# after_app_uninstall = "mtcpl.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mtcpl.notifications.get_notification_config"

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
# 		"mtcpl.tasks.all"
# 	],
# 	"daily": [
# 		"mtcpl.tasks.daily"
# 	],
# 	"hourly": [
# 		"mtcpl.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mtcpl.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mtcpl.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mtcpl.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mtcpl.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mtcpl.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mtcpl.utils.before_request"]
# after_request = ["mtcpl.utils.after_request"]

# Job Events
# ----------
# before_job = ["mtcpl.utils.before_job"]
# after_job = ["mtcpl.utils.after_job"]

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
# 	"mtcpl.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


# Short Leave + Half Day customization
# ------------------------------------
override_doctype_class = {
	"Leave Application": "mtcpl.overrides.leave_application.CustomLeaveApplication",
	"Shift Type": "mtcpl.overrides.shift_type.CustomShiftType",
}

doctype_js = {"Leave Application": "public/js/leave_application.js"}

doc_events = {
	"Attendance": {"on_submit": "mtcpl.api.short_leave.flag_short_leave_on_attendance"},
}

scheduler_events = {
	# idempotent: skips employees who already have this month's allocation
	"cron": {
		"30 0 * * *": ["mtcpl.api.short_leave.allocate_monthly_short_leave"],
	},
}

# Short Leave customization
fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Leave Type-custom_is_monthly_allocated",
					"Leave Type-custom_number_of_leaves_per_month_",
					"Leave Application-custom_short_leave",
					"Leave Application-custom_short_leave_date",
					"Leave Application-custom_short_leave_section",
					"Leave Application-custom_short_leave_from_time",
					"Leave Application-custom_short_leave_to_time",
					"Leave Application-custom_short_leave_hours",
					"Attendance-custom_short_leave_applied",
					"Attendance-custom_short_leave_hours",
					"Attendance-custom_short_leave_source",
					"Attendance-custom_short_leave_application",
				],
			]
		],
	},
]
