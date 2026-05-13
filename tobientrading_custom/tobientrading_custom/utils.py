# -*- coding: utf-8 -*-
# Copyright (c) 2023-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import erpnextswiss.erpnextswiss.attach_pdf
from tobientrading_custom.tobientrading_custom.doctype.supplier_packaging_spec.supplier_packaging_spec import get_pallet_details

@frappe.whitelist()
def apply_origins_to_variants(template_item_code, origins):
    if type(origins) == str:
        origins = json.loads(origins)

    items = frappe.get_all("Item", filters={'variant_of': template_item_code}, fields=['name'])

    for i in items:
        item = frappe.get_doc("Item", i['name'])
        item.origins = []
        for o in origins:
            item.append("origins", {'country_of_origin': o})
        item.save()

    return

@frappe.whitelist()
def attach_tds_pdfs(sales_order):
    so_doc = frappe.get_doc("Sales Order", sales_order)

    crawled_items = []
    # get technical data sheets
    for i in so_doc.items:
        if i.item_code in crawled_items:        # prevent attaching multiple TDS for the same item
            continue
        crawled_items.append(i.item_code)
        tds = frappe.get_value("Item", i.item_code, "technical_data_sheet")
        if tds:
            # find all files attached to this tds
            pdfs = frappe.get_all("File",
                filters={
                    'attached_to_doctype': 'Technical Data Sheet',
                    'attached_to_name': tds
                },
                fields=['name']
            )
            for pdf in pdfs:
                so_pdf = frappe.get_doc(
                    frappe.get_doc("File", pdf['name']).as_dict()
                )
                so_pdf.update({
                    'attached_to_doctype': 'Sales Order',
                    'attached_to_name': sales_order
                })
                so_pdf.insert()

            frappe.db.commit()

    return

# Called by doc_events hook when purchasing or sales docs are submitted
def attach_pdf_hook(doc, event=None):
    fallback_language = frappe.db.get_single_value("System Settings", "language") or "en"
    args = {
        "doctype": doc.doctype,
        "name": doc.name,
        "title": getattr(doc, "title", doc.name),
        "lang": getattr(doc, "language", fallback_language),
    }
    erpnextswiss.erpnextswiss.attach_pdf.execute(**args)
    if doc.doctype == 'Sales Order':
        attach_tds_pdfs(doc.name)
    elif doc.doctype == 'Delivery Note' and doc.tax_category in ['Umsatzsteuer EU - IGD','Umsatzsteuer EU - IGL','Umsatzsteuer Export']:
        gb = args.copy()
        gb['print_format'] = 'Gelangensbestätigung Standard'
        gb['file_name'] = "VAT_{0}_to_sign.pdf".format(doc.name.replace(" ", "-").replace("/", "-"))
        erpnextswiss.erpnextswiss.attach_pdf.execute(**gb)

@frappe.whitelist()
def get_emergency_contact(dt, dn):
    contacts = frappe.db.sql("""
        SELECT
            `tabContact`.`name`,
            `tabContact`.`first_name`,
            `tabContact`.`last_name`,
            `tabContact`.`phone`
        FROM `tabContact`
        LEFT JOIN `tabDynamic Link` ON
            `tabDynamic Link`.`parent` = `tabContact`.`name`
            AND `tabDynamic Link`.`parenttype` = "Contact"
            AND `tabDynamic Link`.`link_doctype` = "{dt}"
        WHERE `tabDynamic Link`.`link_name` = "{dn}"
            AND `tabContact`.`is_emergency_contact` = 1
        ;
    """.format(dt=dt, dn=dn), as_dict=True)

    return contacts


@frappe.whitelist()
def create_batches_from_po(po_no):
    po = frappe.get_doc("Purchase Order", po_no)

    if not po.items:
        frappe.throw("No items found in this Purchase Order.")

    created_batches = []
    skipped_batches = []
    item_count = len(po.items)
    today = frappe.utils.nowdate()

    for idx, item in enumerate(po.items, start=1):
        batch_id = po.name if item_count == 1 else f"{po.name}-{idx}"

        # Check if batch already exists
        existing = frappe.db.exists("Batch", {"batch_id": batch_id})
        if existing:
            skipped_batches.append(batch_id)
            continue

        country_of_origin = item.get('country_of_origin')
        if not country_of_origin:
            country_of_origin = frappe.db.get_value("Item", item.item_code, "country_of_origin")

        if not country_of_origin:
            frappe.throw("Please set 'Country of Origin' for Item " + item.item_code)

        try:
            # Fetch expiry-related settings from Item
            item_doc = frappe.get_doc("Item", item.item_code)
            manufacturing_date = today
            expiry_date = None

            if item_doc.has_expiry_date and item_doc.shelf_life_in_days and item_doc.shelf_life_in_days > 0:
                expiry_date = frappe.utils.add_days(today, item_doc.shelf_life_in_days)
            elif item_doc.has_expiry_date and item_doc.shelf_life_in_days == 0:
                expiry_date = today

            # Prepare batch values
            batch_values = frappe._dict({
                "doctype": "Batch",
                "item": item.item_code,
                "batch_id": batch_id,
                "supplier": po.supplier,
                "manufacturing_date": manufacturing_date,
                "workflow_state": "Pending",
                "country_of_origin": country_of_origin
            })

            if expiry_date:
                batch_values.expiry_date = expiry_date

            if item.get('packaging_spec'):
                pspec_doc = frappe.get_doc("Supplier Packaging Spec", item.packaging_spec)
                batch_values.packaging_spec = item.packaging_spec
                batch_values.package_weight = item.package_weight
                batch_values.pallet_type = pspec_doc.pallet_type
                batch_values.pallet_max_height = pspec_doc.pallet_max_height
                batch_values.packaging_type = pspec_doc.packaging_type
                batch_values.package_tare = pspec_doc.package_tare
                batch_values.package_length = pspec_doc.package_length
                batch_values.package_width = pspec_doc.package_width
                batch_values.package_height = pspec_doc.package_height

                pallet_doc = frappe.get_doc("Pallet Type", pspec_doc.pallet_type)
                batch_values.pallet_tare = pallet_doc.tare
                batch_values.pallet_length = pallet_doc.length
                batch_values.pallet_width = pallet_doc.width
                batch_values.pallet_base_height = pallet_doc.height

            batch = frappe.get_doc(batch_values)
            batch.insert()
            item.batch_no = batch_id
            item.save()
            frappe.db.commit()
            created_batches.append(f'<a href="/app/batch/{batch.name}">{batch.name}</a>')

        except Exception as e:
            short_msg = "Failed to create batch " + batch_id
            frappe.log_error(title=short_msg, message=str(e))
            skipped_batches.append(batch_id)

    # Prepare response message
    message_parts = []
    if created_batches:
        message_parts.append(f"{len(created_batches)} Batch(es) created: {', '.join(created_batches)}")
    else:
        message_parts.append("No Batch(es) created.")

    if skipped_batches:
        message_parts.append(f"<br><hr><span style='color: red;'>Skipped existing/failed Batch ID(s): {', '.join(skipped_batches)}</span>")

    frappe.response['message'] = "".join(message_parts)


@frappe.whitelist()
def get_batch_info(item_code):
    sql_query = """
        SELECT
          `batches`.`item_code`,
          `batches`.`batch_no`,
          `batches`.`qty`,
          `batches`.`stock_uom`,
          `batches`.`first_transaction_date`,
          `tabBatch`.`pallet_length`, `tabBatch`.`pallet_width`, `tabBatch`.`pallet_base_height`, `tabBatch`.`pallet_max_height`,
          `tabBatch`.`package_length`, `tabBatch`.`package_width`, `tabBatch`.`package_height`, `tabBatch`.`package_weight`
        FROM (
          SELECT `item_code`, IFNULL(`batch_no`, 'None') AS `batch_no`, SUM(`actual_qty`) AS `qty`, `stock_uom`, MIN(`posting_date`) AS `first_transaction_date`
          FROM `tabStock Ledger Entry`
          WHERE `item_code` = '{item_code}'
          GROUP BY `batch_no`
          ORDER BY `first_transaction_date`
        ) AS `batches`
        INNER JOIN `tabBatch` ON `batches`.`batch_no` = `tabBatch`.`name`
        WHERE `qty` != 0;""".format(item_code=item_code)
    data = frappe.db.sql(sql_query, as_dict=1)
    for row in data:
        pallet_details = get_pallet_details(row.pallet_length, row.pallet_width, row.pallet_base_height, row.pallet_max_height, row.package_length, row.package_width, row.package_height)
        row.update(pallet_details)
    return data


@frappe.whitelist()
def set_batch_packaging_specs(batch, specs):
    if type(specs) == str:
        specs = json.loads(specs)

    pallet_specs = {
        'tare': specs.get('pallet_tare'),
        'height': specs.get('pallet_base_height'),
        'length': specs.get('pallet_length'),
        'width': specs.get('pallet_width')
    }
    packspecs =  {key: specs.get(key) for key in [
        'pallet_type', 'pallet_max_height', 'packaging_type', 'package_length', 'package_width', 'package_height', 'package_tare',
    ]}
    pallet_doc = frappe.get_doc("Pallet Type", specs['pallet_type'])
    pallet_doc.update(pallet_specs)
    pallet_doc.save()
    packspec_doc = frappe.get_doc("Supplier Packaging Spec", specs['packaging_spec'])
    packspec_doc.update(packspecs)
    packspec_doc.save()
    batch_doc = frappe.get_doc("Batch", batch)
    batch_doc.update({'package_weight': specs.get('package_weight'), 'packaging_spec': specs['packaging_spec']})
    batch_doc.save()
    frappe.db.commit()