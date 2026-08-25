# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Transport Order used to reference exactly one Purchase Order and one Sales
# Order via the single-value Link fields `purchase_order` / `sales_order`. These
# have been replaced by the `po_so_links` child table (core "Dynamic Link"),
# which lets a Transport Order reference several POs and/or SOs at once.
#
# This patch copies every legacy `purchase_order` / `sales_order` reference into
# a `po_so_links` row and then clears the stale single-value fields. It runs in
# [post_model_sync] so that sync_all() has already added the `po_so_links` field
# to the Transport Order schema (the child rows themselves live in the core
# `tabDynamic Link`, which always exists).
#
# `link_title` mirrors the client script: the supplier name for a Purchase Order
# row, the customer name for a Sales Order row.
#
# The insert is done in raw SQL (bypassing the ORM) on purpose: many Transport
# Orders are submitted (docstatus 1) or cancelled (docstatus 2), and appending a
# child row through the document API would be rejected. The child row inherits
# the parent's docstatus. Re-running is safe: an already-migrated link is
# skipped, and cleared legacy fields are not picked up a second time.

import frappe


def execute():
    has_po = frappe.db.has_column("Transport Order", "purchase_order")
    has_so = frappe.db.has_column("Transport Order", "sales_order")
    if not (has_po or has_so):
        print("Transport Order: no legacy purchase_order/sales_order columns - nothing to migrate")
        return

    orders = frappe.db.sql("""
        SELECT `name`, `purchase_order`, `sales_order`, `docstatus`
        FROM `tabTransport Order`
        WHERE IFNULL(`purchase_order`, '') != '' OR IFNULL(`sales_order`, '') != ''
    """, as_dict=True)

    print("Transport Order: migrating PO/SO links for {0} record(s)".format(len(orders)))

    for order in orders:
        # Continue the idx from any rows the parent might already have
        idx = frappe.db.sql("""
            SELECT IFNULL(MAX(`idx`), 0) FROM `tabDynamic Link`
            WHERE `parenttype` = 'Transport Order'
              AND `parentfield` = 'po_so_links'
              AND `parent` = %s
        """, order.name)[0][0]

        for link_doctype, link_name in (
            ("Purchase Order", order.purchase_order),
            ("Sales Order", order.sales_order),
        ):
            if not link_name:
                continue
            if frappe.db.exists("Dynamic Link", {
                "parenttype": "Transport Order",
                "parentfield": "po_so_links",
                "parent": order.name,
                "link_doctype": link_doctype,
                "link_name": link_name,
            }):
                # Already migrated on an earlier run
                continue
            idx += 1
            _insert_po_so_link(order, link_doctype, link_name, idx)

    # Clear the stale single-value references now that they live in po_so_links
    if has_po:
        frappe.db.sql("UPDATE `tabTransport Order` SET `purchase_order` = NULL WHERE IFNULL(`purchase_order`, '') != ''")
    if has_so:
        frappe.db.sql("UPDATE `tabTransport Order` SET `sales_order` = NULL WHERE IFNULL(`sales_order`, '') != ''")

    frappe.db.commit()
    print("Transport Order: done ({0} record(s) processed)".format(len(orders)))


def _insert_po_so_link(order, link_doctype, link_name, idx):
    if link_doctype == "Purchase Order":
        link_title = frappe.db.get_value("Purchase Order", link_name, "supplier_name")
    else:
        link_title = frappe.db.get_value("Sales Order", link_name, "customer_name")

    frappe.db.sql("""
        INSERT INTO `tabDynamic Link`
            (`name`, `creation`, `modified`, `owner`, `modified_by`, `docstatus`,
             `idx`, `parent`, `parenttype`, `parentfield`,
             `link_doctype`, `link_name`, `link_title`)
        VALUES
            (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', %(docstatus)s,
             %(idx)s, %(parent)s, 'Transport Order', 'po_so_links',
             %(link_doctype)s, %(link_name)s, %(link_title)s)
    """, {
        "name": frappe.generate_hash(length=10),
        "docstatus": order.docstatus,
        "idx": idx,
        "parent": order.name,
        "link_doctype": link_doctype,
        "link_name": link_name,
        "link_title": link_title,
    })
