# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Fills `Sales Invoice.custom_delivery_months` on submitted and cancelled
# invoices with the distinct "YYYY-MM" of their items' delivery dates. New
# invoices get the value from the on_submit / on_update_after_submit hook.
#
# Custom fields are synced only after all patches have run, so the field is
# created on demand here if the site does not have it yet.

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from tobientrading_custom.tobientrading_custom.utils import get_delivery_months

FIELDNAME = "custom_delivery_months"


def execute():
    create_field_if_missing()

    delivery_dates = {}
    for row in frappe.db.sql("""
        SELECT `si`.`name` AS `invoice`, `sii`.`delivery_date` AS `delivery_date`
        FROM `tabSales Invoice` AS `si`
        JOIN `tabSales Invoice Item` AS `sii` ON `sii`.`parent` = `si`.`name`
        WHERE `si`.`docstatus` IN (1, 2)
          AND `sii`.`delivery_date` IS NOT NULL""", as_dict=True):
        delivery_dates.setdefault(row.invoice, []).append(row.delivery_date)

    print("Setting delivery months on {0} Sales Invoices...".format(len(delivery_dates)))

    for count, (invoice, dates) in enumerate(delivery_dates.items(), start=1):
        frappe.db.set_value("Sales Invoice", invoice, FIELDNAME, get_delivery_months(dates),
            update_modified=False)

        if count % 500 == 0:
            frappe.db.commit()
            print("... {0}/{1}".format(count, len(delivery_dates)))

    frappe.db.commit()
    print("Done.")


def create_field_if_missing():
    if frappe.db.has_column("Sales Invoice", FIELDNAME):
        return

    create_custom_fields({
        "Sales Invoice": [{
            "fieldname": FIELDNAME,
            "label": "Delivery Months",
            "fieldtype": "Data",
            "insert_after": "exclude_from_payment_reminder_until",
            "read_only": 1,
            "translatable": 1
        }]
    })
