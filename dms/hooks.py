from . import __version__ as app_version

app_name = "dms"
app_title = "Frappe DMS"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "An easy to use, document sharing and management solution."
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "developers@frappe.io"
app_license = "GNU Affero General Public License v3.0"

website_route_rules = [
    {"from_route": "/dms/<path:app_path>", "to_route": "dms"},
]

add_to_apps_screen = [
    {
        "name": "dms",
        "logo": "/assets/dms/frontend/favicon-310x310.png",
        "title": "DMS",
        "route": "/dms",
        "has_permission": "dms.api.product.access_app",
    }
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dms/css/dms.css"
# app_include_js = "/assets/dms/js/dms.js"

# include js, css files in header of web template
# web_include_css = "/assets/dms/css/dms.css"
# web_include_js = "/assets/dms/js/dms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dms/public/scss/website"

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

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "dms"

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
# 	"methods": "dms.utils.jinja_methods",
# 	"filters": "dms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "dms.install.before_install"
after_install = "dms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "dms.uninstall.before_uninstall"
# after_uninstall = "dms.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#

has_permission = {
    "DMS File": "dms.api.permissions.user_has_permission",
}

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


# fixtures = [{"dt": "Role", "filters": [["role_name", "like", "DMS %"]]}]

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": ["dms.api.files.auto_delete_from_trash", "dms.api.files.clear_deleted_files"],
    "hourly": ["dms.api.permissions.auto_delete_expired_perms"],
}

# Testing
# -------

# before_tests = "dms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "dms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


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
# 	"dms.auth.validate"
# ]


signup_form_template = "templates/signup.html"

# # Add OCR API endpoints
# override_whitelisted_methods = getattr(globals(), 'override_whitelisted_methods', {})
# override_whitelisted_methods.update({
#     'dms.api.ocr.upload': 'dms.api.ocr.upload',
#     'dms.api.ocr.list': 'dms.api.ocr.list',
# })

# Optionally, add to app's REST API routes if needed
# See Frappe docs for custom route registration if required
