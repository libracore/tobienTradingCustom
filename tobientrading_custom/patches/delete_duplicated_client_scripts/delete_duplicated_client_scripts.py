# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Delete Client Scripts that have been migrated into versioned .js files in this
# app. They are now duplicated (DB record + .js), so the DB records are removed
# on rollout to avoid the script running twice.

import frappe

# Client Script names (= ID) that are now shipped as .js files instead
DUPLICATED_CLIENT_SCRIPTS = [
    "Pricing Rule on Blanket Order",
    "Blanket Order - Pull addresses",
    "Item Approval - Senoric Parameters",
]


def execute():
    for name in DUPLICATED_CLIENT_SCRIPTS:
        if frappe.db.exists("Client Script", name):
            frappe.delete_doc("Client Script", name, ignore_permissions=True)
            print("Deleted duplicated Client Script '{0}'.".format(name))
        else:
            print("Client Script '{0}' not found - nothing to delete.".format(name))
