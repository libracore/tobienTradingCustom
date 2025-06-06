# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "tobientrading_custom"
app_title = "Tobientrading Custom"
app_publisher = "libracore AG"
app_description = "Tobien Trading Customizations"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@libracore.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tobientrading_custom/css/tobientrading_custom.css"
app_include_js = [
    "/assets/tobientrading_custom/js/tobien_common.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/tobientrading_custom/css/tobientrading_custom.css"
# web_include_js = "/assets/tobientrading_custom/js/tobientradingtemplates.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Opportunity" : "public/js/opportunity.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "Delivery Note": "public/js/delivery_note.js",
    "Sales Order": "public/js/sales_order.js",
    "Quotation": "public/js/quotation.js",
    "Payment Reminder": "public/js/payment_reminder.js",
    "Material Request": "public/js/material_request.js",
    "Request for Quotation": "public/js/request_for_quotation.js",
    "Supplier Quotation": "public/js/supplier_quotation.js",
    "Purchase Order": "public/js/purchase_order.js",
    "Purchase Receipt": "public/js/purchase_receipt.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Item": "public/js/item.js",
    "Supplier": "public/js/supplier.js",
    "Supplier": "public/js/customer.js"
}
doctype_list_js = {
    "Certificate of Analysis" : "public/js/certificate_of_analysis_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "tobientrading_custom.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "tobientrading_custom.install.before_install"
# after_install = "tobientrading_custom.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tobientrading_custom.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Measurement Parameter": {
		"on_update": "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis_result.certificate_of_analysis_result.update_test_type_and_subcategory"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tobientrading_custom.tasks.all"
# 	],
# 	"daily": [
# 		"tobientrading_custom.tasks.daily"
# 	],
# 	"hourly": [
# 		"tobientrading_custom.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tobientrading_custom.tasks.weekly"
# 	]
# 	"monthly": [
# 		"tobientrading_custom.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "tobientrading_custom.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tobientrading_custom.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tobientrading_custom.task.get_dashboard_data"
# }

fixtures = [{
    'doctype': 'Print Format',
    'filters': [['name', 'in', [
        "Lot Print Format"
    ]]]
}]
