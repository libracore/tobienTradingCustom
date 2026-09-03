# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Copy of ERPNext's "General Ledger" report with an additional "Delivery Date"
# column for Sales Invoices. The delivery date is resolved per invoice in this
# order (first hit wins), because `Sales Invoice.delivery_date` is often empty:
#
#   1. `Sales Invoice.delivery_date`                        (custom field)
#   2. delivery date of the Sales Order linked on the items (parent field, else
#      the linked Sales Order Item)
#   3. `delivery_date` of the first Sales Invoice Item      (custom field)

import frappe
from frappe import _

from erpnext.accounts.report.general_ledger.general_ledger import execute as get_general_ledger


def execute(filters=None):
    columns, data = get_general_ledger(filters)

    if not columns:
        return columns, data

    add_delivery_date_column(columns)
    set_delivery_dates(data)

    return columns, data


def add_delivery_date_column(columns):
    """Insert the Delivery Date column right after Posting Date."""
    column = {
        "label": _("Delivery Date"),
        "fieldname": "delivery_date",
        "fieldtype": "Date",
        "width": 120
    }

    for idx, col in enumerate(columns):
        if col.get("fieldname") == "posting_date":
            columns.insert(idx + 1, column)
            return

    columns.append(column)


def set_delivery_dates(data):
    invoices = list({
        d.get("voucher_no") for d in data
        if d.get("voucher_type") == "Sales Invoice" and d.get("voucher_no")
    })

    delivery_dates = get_delivery_dates(invoices)

    for d in data:
        if d.get("voucher_type") == "Sales Invoice":
            d["delivery_date"] = delivery_dates.get(d.get("voucher_no"))


def get_delivery_dates(invoices):
    """Return {sales invoice: delivery date} for the given invoices."""
    delivery_dates = {}

    if not invoices:
        return delivery_dates

    # 1) delivery date maintained directly on the Sales Invoice
    for d in frappe.db.sql("""
        SELECT `name`, `delivery_date`
        FROM `tabSales Invoice`
        WHERE `name` IN %(invoices)s
          AND `delivery_date` IS NOT NULL""", {"invoices": invoices}, as_dict=True):
        delivery_dates[d.name] = d.delivery_date

    missing = [i for i in invoices if i not in delivery_dates]
    if not missing:
        return delivery_dates

    # 2) delivery date of the Sales Order the invoice items were billed from.
    #    Ordered by descending idx so that the first item's Sales Order wins.
    for d in frappe.db.sql("""
        SELECT `sii`.`parent` AS `invoice`,
               IFNULL(`so`.`delivery_date`, `soi`.`delivery_date`) AS `delivery_date`
        FROM `tabSales Invoice Item` AS `sii`
        JOIN `tabSales Order` AS `so` ON `so`.`name` = `sii`.`sales_order`
        LEFT JOIN `tabSales Order Item` AS `soi` ON `soi`.`name` = `sii`.`so_detail`
        WHERE `sii`.`parent` IN %(invoices)s
          AND IFNULL(`so`.`delivery_date`, `soi`.`delivery_date`) IS NOT NULL
        ORDER BY `sii`.`parent` ASC, `sii`.`idx` DESC""", {"invoices": missing}, as_dict=True):
        delivery_dates[d.invoice] = d.delivery_date

    missing = [i for i in missing if i not in delivery_dates]
    if not missing:
        return delivery_dates

    # 3) delivery date on the first Sales Invoice Item (descending idx, see above)
    for d in frappe.db.sql("""
        SELECT `parent` AS `invoice`, `delivery_date`
        FROM `tabSales Invoice Item`
        WHERE `parent` IN %(invoices)s
          AND `delivery_date` IS NOT NULL
        ORDER BY `parent` ASC, `idx` DESC""", {"invoices": missing}, as_dict=True):
        delivery_dates[d.invoice] = d.delivery_date

    return delivery_dates
