# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 110},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 160},
        {"label": _("Item Code (SO)"), "fieldname": "so_item_code", "fieldtype": "Link", "options": "Item", "width": 110},
        {"label": _("Item Name (SO)"), "fieldname": "so_item_name", "fieldtype": "Data", "width": 160},
        {"label": _("Qty (SO)"), "fieldname": "so_qty", "fieldtype": "Float", "width": 90},
        {"label": _("Delivery Note"), "fieldname": "delivery_note", "fieldtype": "Link", "options": "Delivery Note", "width": 130},
        {"label": _("Against Sales Order (DN)"), "fieldname": "dn_against_so", "fieldtype": "Link", "options": "Sales Order", "width": 130},
        {"label": _("Item Code (DN)"), "fieldname": "dn_item_code", "fieldtype": "Link", "options": "Item", "width": 110},
        {"label": _("Item Name (DN)"), "fieldname": "dn_item_name", "fieldtype": "Data", "width": 160},
        {"label": _("Delivery Date (DN)"), "fieldname": "dn_delivery_date", "fieldtype": "Date", "width": 100},
        {"label": _("Qty (DN)"), "fieldname": "dn_qty", "fieldtype": "Float", "width": 90},
        {"label": _("Shipping Address (DN)"), "fieldname": "dn_shipping_address", "fieldtype": "Link", "options": "Address", "width": 160},
        {"label": _("Transport Order"), "fieldname": "transport_order", "fieldtype": "Link", "options": "Transport Order", "width": 130},
        {"label": _("Loading Address"), "fieldname": "loading_address", "fieldtype": "Link", "options": "Address", "width": 160},
        {"label": _("Shipping Address (TO)"), "fieldname": "to_shipping_address", "fieldtype": "Link", "options": "Address", "width": 160},
        {"label": _("Linked Sales Order (TO)"), "fieldname": "to_link_name", "fieldtype": "Link", "options": "Sales Order", "width": 130},
        {"label": _("Logistic Company"), "fieldname": "logistic_company", "fieldtype": "Link", "options": "Supplier", "width": 130},
    ]


def get_data(filters):
    conditions = ""
    if filters.get("company"):
        conditions += " AND `so`.`company` = %(company)s"
    if filters.get("customer"):
        conditions += " AND `so`.`customer` = %(customer)s"
    if filters.get("transport_order"):
        conditions += " AND `tor`.`name` = %(transport_order)s"
    if filters.get("from_date"):
        conditions += " AND `so`.`transaction_date` >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND `so`.`transaction_date` <= %(to_date)s"

    # One row per SO item, per TO planning it and per DN item delivering it
    return frappe.db.sql("""
        SELECT
            `so`.`name` AS `sales_order`,
            `so`.`customer`,
            `so`.`customer_name`,
            `soi`.`item_code` AS `so_item_code`,
            `soi`.`item_name` AS `so_item_name`,
            `soi`.`qty` AS `so_qty`,
            `dn`.`name` AS `delivery_note`,
            `dni`.`against_sales_order` AS `dn_against_so`,
            `dni`.`item_code` AS `dn_item_code`,
            `dni`.`item_name` AS `dn_item_name`,
            `dni`.`delivery_date` AS `dn_delivery_date`,
            `dni`.`qty` AS `dn_qty`,
            `dn`.`shipping_address_name` AS `dn_shipping_address`,
            `tor`.`name` AS `transport_order`,
            `tor`.`loading_address`,
            `tor`.`company_shipping_address` AS `to_shipping_address`,
            `tdl`.`link_name` AS `to_link_name`,
            `tor`.`logistic_company`
        FROM `tabSales Order` AS `so`
        JOIN `tabSales Order Item` AS `soi` ON `soi`.`parent` = `so`.`name`
        LEFT JOIN (
            (SELECT DISTINCT `parent`, `sales_order_item` FROM `tabTransport Table Item`) AS `toi`
            JOIN `tabTransport Order` AS `tor` ON `tor`.`name` = `toi`.`parent` AND `tor`.`docstatus` < 2
        ) ON `toi`.`sales_order_item` = `soi`.`name`
        LEFT JOIN `tabDynamic Link` AS `tdl` ON `tdl`.`parenttype` = "Transport Order"
            AND `tdl`.`parent` = `tor`.`name`
            AND `tdl`.`link_doctype` = "Sales Order"
            AND `tdl`.`link_name` = `so`.`name`
        LEFT JOIN (
            `tabDelivery Note Item` AS `dni`
            JOIN `tabDelivery Note` AS `dn` ON `dn`.`name` = `dni`.`parent` AND `dn`.`docstatus` = 1
        ) ON `dni`.`so_detail` = `soi`.`name`
            AND IFNULL(`dn`.`transport_order`, "") IN ("", IFNULL(`tor`.`name`, ""))
        WHERE `so`.`docstatus` = 1
            {conditions}
        ORDER BY `so`.`name`, `soi`.`idx`, `tor`.`name`, `dn`.`name`, `dni`.`idx`
    """.format(conditions=conditions), filters, as_dict=True)
