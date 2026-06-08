# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from tobientrading_custom.tobientrading_custom.utils import get_batch_info
from erpnext.stock.get_item_details import get_conversion_factor

class TransportOrder(Document):
	pass

@frappe.whitelist()
def get_matching_batches(sales_order, sales_order_item):
    so_item_doc = frappe.get_doc("Sales Order Item", sales_order_item)
    item_doc = frappe.get_doc("Item", so_item_doc.item_code)
    batch_info = get_batch_info(so_item_doc.item_code)
    status = 'OK'
    # Get the required qty in the Item's stock UOM
    remaining_qty = so_item_doc.qty
    if so_item_doc.uom != item_doc.stock_uom:
        conv_factor = get_conversion_factor(so_item_doc.item_code, so_item_doc.uom)
        remaining_qty *= conv_factor
    # Starting with the oldest Batch, use as much as required
    batches = []
    for batch in batch_info:
        if batch.stock_uom != item_doc.stock_uom:
            conv_factor = get_conversion_factor(so_item_doc.item_code, batch.stock_uom)
            batch.qty *= conv_factor
        qty_to_use = min(batch.qty, remaining_qty)
        batches.append({
            'batch_no': batch.batch_no,
            'qty': qty_to_use,
            'uom': item_doc.stock_uom
        })
        remaining_qty -= qty_to_use
        if remaining_qty == 0:
            break
    if remaining_qty > 0:
        status = "The available stock does not cover the full order amount ({0} {1} missing)".format(remaining_qty, item_doc.stock_uom)
    return {'status': status, 'batches': batches}

@frappe.whitelist()
def create_delivery_note(transport_order):
    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

    to_doc = frappe.get_doc("Transport Order", transport_order)
    if to_doc.docstatus != 1:
        frappe.throw(_("The Transport Order must be submitted before creating a Delivery Note."))
    if not to_doc.sales_order:
        frappe.throw(_("This Transport Order is not linked to a Sales Order."))

    # Build the Delivery Note header from the Sales Order, but skip the item mapping:
    # we supply our own line items from the Transport Order instead.
    dn = make_delivery_note(to_doc.sales_order, kwargs={"skip_item_mapping": True})

    # Look up the Sales Order items so we can copy item-level details (warehouse, cost
    # center, project) and keep the reference to the originating Sales Order Item intact.
    so_doc = frappe.get_doc("Sales Order", to_doc.sales_order)
    so_items = {row.name: row for row in so_doc.items}

    for item in to_doc.items:
        dn_item = dn.append("items", {})
        dn_item.item_code = item.item_code
        dn_item.qty = flt(item.quantity)
        dn_item.uom = item.uom
        dn_item.rate = item.rate
        # Per-item delivery date comes from the Transport Order
        dn_item.delivery_date = to_doc.delivery_date
        if item.batch:
            dn_item.use_serial_batch_fields = 1
            dn_item.batch_no = item.batch
        # Keep the link to the Sales Order Item where available so delivered qty is tracked
        so_item = so_items.get(item.sales_order_item)
        if so_item:
            dn_item.against_sales_order = so_doc.name
            dn_item.so_detail = so_item.name
            dn_item.warehouse = so_item.warehouse
            dn_item.cost_center = so_item.cost_center
            dn_item.project = so_item.project
            # Preserve the description and the tax treatment agreed in the Sales Order,
            # rather than letting get_item_details re-derive them from the Item master.
            dn_item.description = so_item.description
            dn_item.item_tax_template = so_item.item_tax_template
            dn_item.item_tax_rate = so_item.item_tax_rate

    # Flesh out the manually added items (conversion factor, accounts, descriptions, ...)
    # and recompute totals now that the items are in place.
    dn.delivery_date = to_doc.delivery_date
    dn.run_method("set_missing_values")
    dn.run_method("calculate_taxes_and_totals")
    make_packing_list(dn)

    dn.insert(ignore_permissions=True)
    return dn.name