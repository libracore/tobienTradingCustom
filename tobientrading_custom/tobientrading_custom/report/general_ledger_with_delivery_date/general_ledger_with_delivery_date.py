# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Copy of ERPNext's "General Ledger" report with an additional "Delivery Months"
# column, filled from `Sales Invoice.custom_delivery_months` on Sales Invoice
# rows. That field holds the distinct "YYYY-MM" of the invoice items' delivery
# dates (see tobientrading_custom.tobientrading_custom.utils.set_delivery_months).

import frappe
from frappe import _

from erpnext.accounts.report.general_ledger.general_ledger import execute as get_general_ledger

DELIVERY_MONTHS_FIELD = "custom_delivery_months"


def execute(filters=None):
    columns, data = get_general_ledger(filters)

    if not columns:
        return columns, data

    add_delivery_months_column(columns)
    set_delivery_months(data)

    return columns, data


def add_delivery_months_column(columns):
    """Insert the Delivery Months column right after Posting Date."""
    column = {
        "label": _("Delivery Months"),
        "fieldname": "delivery_months",
        "fieldtype": "Data",
        "width": 140
    }

    for idx, col in enumerate(columns):
        if col.get("fieldname") == "posting_date":
            columns.insert(idx + 1, column)
            return

    columns.append(column)


def set_delivery_months(data):
    invoices = list({
        d.get("voucher_no") for d in data
        if d.get("voucher_type") == "Sales Invoice" and d.get("voucher_no")
    })

    delivery_months = get_delivery_months_map(invoices)

    for d in data:
        if d.get("voucher_type") == "Sales Invoice":
            d["delivery_months"] = delivery_months.get(d.get("voucher_no"))


def get_delivery_months_map(invoices):
    """Return {sales invoice: delivery months} for the given invoices."""
    if not invoices:
        return {}

    rows = frappe.db.sql("""
        SELECT `name`, `{fieldname}`
        FROM `tabSales Invoice`
        WHERE `name` IN %(invoices)s
          AND IFNULL(`{fieldname}`, '') != ''""".format(fieldname=DELIVERY_MONTHS_FIELD),
        {"invoices": invoices})

    return dict(rows)
