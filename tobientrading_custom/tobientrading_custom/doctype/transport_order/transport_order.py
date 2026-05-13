# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
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
            qty = batch.qty * conv_factor
        qty_to_use = min(qty, remaining_qty)
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