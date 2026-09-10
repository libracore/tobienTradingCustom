# -*- coding: utf-8 -*-
# Copyright (c) 2023-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import getdate
from tobientrading_custom.tobientrading_custom.doctype.technical_data_sheet.technical_data_sheet import get_current_tds
import json
import erpnextswiss.erpnextswiss.attach_pdf

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


# Attach the right PDF prints of the Technical Data Sheets of all line items to a purchasing or sales doc
def attach_tds_pdf(dest_doc, event=None):
    # Use the purchasing version (different print format) in POs
    pdf_filename_template =  "{0} PO.pdf" if dest_doc.doctype == 'Purchase Order' else "{0}.pdf"
    crawled_items = []
    # get technical data sheets
    for i in dest_doc.items:
        if i.item_code in crawled_items:        # prevent attaching multiple TDS for the same item
            continue
        crawled_items.append(i.item_code)
        tds = get_current_tds(i.item_code)
        if tds:
            # find matching PDF attached to this TDS
            pdf_filename = pdf_filename_template.format(tds.replace(" ", "-").replace("/", "-"))
            pdf_attachment = get_tds_pdf_attachment(pdf_filename, tds)
            if not pdf_attachment:
                tds_doc = frappe.get_doc("Technical Data Sheet", tds)
                if dest_doc.doctype == 'Purchase Order':
                    tds_doc.attach_po_pdf()
                else:
                    attach_pdf_hook(tds_doc)
                pdf_attachment = get_tds_pdf_attachment(pdf_filename, tds)
                if pdf_attachment:
                    frappe.msgprint(_("Missing PDF '{0}' created for Technical Data Sheet '{1}'".format(pdf_filename, tds)), _("Note"))
                else:
                    frappe.throw(_("Error: Failed to create missing PDF '{0}' for Technical Data Sheet '{1}'".format(pdf_filename, tds)));
                    continue

            if pdf_attachment:
                dest_pdf = frappe.get_doc(
                    frappe.get_doc("File", pdf_attachment).as_dict()
                )
                dest_pdf.update({
                    'attached_to_doctype': dest_doc.doctype,
                    'attached_to_name': dest_doc.name
                })
                dest_pdf.insert()

        else: # No TDS found
            frappe.msgprint(_("No Technical Data Sheet found for Item '{0}'".format(i.item_code)), _("Warning"))

    frappe.db.commit()


def get_tds_pdf_attachment(pdf_filename, tds_name):
    pdfs = frappe.get_all("File",
        filters={
            'attached_to_doctype': 'Technical Data Sheet',
            'attached_to_name': tds_name,
            'file_name': pdf_filename
        },
        fields=['name']
    )
    if len(pdfs) > 1:
        frappe.throw(_("Error: Technical Data Sheet '{0}' has more than one matching attachment".format(tds)));
        return None
    elif len(pdfs) == 1:
        return pdfs[0]['name']
    else:
        return None


# Called by doc_events hook when purchasing or sales docs are submitted
def attach_pdf_hook(doc, event=None):
    fallback_language = frappe.db.get_single_value("System Settings", "language") or "en"
    args = {
        "doctype": doc.doctype,
        "name": doc.name,
        "title": doc.get("title") or doc.name,
        "lang": doc.get("language") or fallback_language,
    }
    erpnextswiss.erpnextswiss.attach_pdf.execute(**args)
    if doc.doctype == 'Delivery Note' and doc.tax_category in ['Umsatzsteuer EU - IGD','Umsatzsteuer EU - IGL','Umsatzsteuer Export']:
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
            # Prepare batch values
            batch_values = frappe._dict({
                "doctype": "Batch",
                "item": item.item_code,
                "batch_id": batch_id,
                "supplier": po.supplier,
                "manufacturing_date": today,
                "workflow_state": "Pending",
                "country_of_origin": country_of_origin
            })

            item_doc = frappe.get_doc("Item", item.item_code)
            expiry_date = _get_batch_expiry_date(item_doc, today)
            if expiry_date:
                batch_values.expiry_date = expiry_date

            if item.get('packaging_spec'):
                _apply_packaging_spec_to_batch(batch_values, item.packaging_spec, item.package_weight)

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


def _get_batch_expiry_date(item_doc, reference_date):
    """Return the batch expiry date for an item, or None if it does not expire."""
    if not item_doc.has_expiry_date:
        return None
    if item_doc.shelf_life_in_days and item_doc.shelf_life_in_days > 0:
        return frappe.utils.add_days(reference_date, item_doc.shelf_life_in_days)
    if item_doc.shelf_life_in_days == 0:
        return reference_date
    return None


def get_next_mo_batch_code():
    """Return the next free batch id of the format 'MO-######' (6 digits)."""
    last = frappe.db.sql("""
        SELECT `batch_id`
        FROM `tabBatch`
        WHERE `batch_id` REGEXP '^MO-[0-9]{6}$'
        ORDER BY CAST(SUBSTRING(`batch_id`, 4) AS UNSIGNED) DESC
        LIMIT 1
    """)
    next_num = (int(last[0][0][3:]) + 1) if last else 1
    return "MO-{:06d}".format(next_num)


def _apply_packaging_spec_to_batch(batch_values, packaging_spec_name, package_weight):
    """Copy pallet/package details from a Supplier Packaging Spec onto batch_values."""
    pspec_doc = frappe.get_doc("Supplier Packaging Spec", packaging_spec_name)
    batch_values.packaging_spec = packaging_spec_name
    batch_values.package_weight = package_weight
    # net weight per pallet = packages per pallet * package weight (cf. batch.js)
    batch_values.net_weight_per_pallet = (pspec_doc.packages_per_pallet or 0) * (package_weight or 0)
    batch_values.pallet_type = pspec_doc.pallet_type
    batch_values.pallet_max_height = pspec_doc.pallet_max_height
    batch_values.packaging_type = pspec_doc.packaging_type
    batch_values.package_tare = pspec_doc.package_tare
    batch_values.package_length = pspec_doc.package_length
    batch_values.package_width = pspec_doc.package_width
    batch_values.package_height = pspec_doc.package_height
    batch_values.packages_per_layer = pspec_doc.packages_per_layer
    batch_values.layers_per_pallet = pspec_doc.layers_per_pallet

    pallet_doc = frappe.get_doc("Pallet Type", pspec_doc.pallet_type)
    batch_values.pallet_tare = pallet_doc.tare
    batch_values.pallet_length = pallet_doc.length
    batch_values.pallet_width = pallet_doc.width
    batch_values.pallet_base_height = pallet_doc.height


@frappe.whitelist()
def create_mo_batch(work_order, packaging_spec):
    """Create a Batch for the manufactured item of a Work Order.

    The batch id is the next free code of the format 'MO-######'. The package
    weight is taken from the packaging spec's item assignment subtable.
    """
    wo = frappe.get_doc("Work Order", work_order)

    if not wo.production_item:
        frappe.throw(_("No production item set on this Work Order."))
    if not wo.contract_processing_supplier:
        frappe.throw(_("Please set the Contract Processing Supplier first."))

    # Resolve the package weight from the spec's item assignment subtable
    pspec_doc = frappe.get_doc("Supplier Packaging Spec", packaging_spec)
    assignment = next((a for a in pspec_doc.items if a.item == wo.production_item), None)
    if not assignment:
        frappe.throw(_("The packaging spec {0} contains no details for item {1}.").format(
            packaging_spec, wo.production_item))

    today = frappe.utils.nowdate()
    batch_id = get_next_mo_batch_code()

    batch_values = frappe._dict({
        "doctype": "Batch",
        "item": wo.production_item,
        "batch_id": batch_id,
        "supplier": wo.contract_processing_supplier,
        "manufacturing_date": today,
        "workflow_state": "Pending",
    })

    country_of_origin = frappe.db.get_value("Item", wo.production_item, "country_of_origin")
    if country_of_origin:
        batch_values.country_of_origin = country_of_origin

    item_doc = frappe.get_doc("Item", wo.production_item)
    expiry_date = _get_batch_expiry_date(item_doc, today)
    if expiry_date:
        batch_values.expiry_date = expiry_date

    _apply_packaging_spec_to_batch(batch_values, packaging_spec, assignment.nominal_package_weight)

    batch = frappe.get_doc(batch_values)
    batch.insert()
    frappe.db.commit()

    frappe.response['message'] = _("Batch created: ") + \
        '<a href="/app/batch/{0}">{0}</a>'.format(batch.name)


@frappe.whitelist()
def get_batch_info(item_code, include_expired_disabled=True):
    # NOTE: Newer Stock Ledger Entries store their batch via a "Serial and Batch
    #       Bundle" instead of the SLE's own `batch_no` column (which is then NULL)
    sql_query = """
        SELECT
          `batches`.`item_code`,
          `batches`.`batch_no`,
          `batches`.`qty`,
          `batches`.`stock_uom`,
          `batches`.`first_transaction_date`,
          `tabBatch`.`pallet_length`, `tabBatch`.`pallet_width`, `tabBatch`.`pallet_base_height`, `tabBatch`.`pallet_max_height`,
          `tabBatch`.`package_length`, `tabBatch`.`package_width`, `tabBatch`.`package_height`, `tabBatch`.`package_weight`,
          `tabBatch`.`packages_per_layer`, `tabBatch`.`layers_per_pallet`,
          `tabBatch`.`packages_per_layer` * `tabBatch`.`layers_per_pallet` AS `packages_per_pallet`
        FROM (
          SELECT `item_code`, `batch_no`, SUM(`actual_qty`) AS `qty`, `stock_uom`, MIN(`posting_date`) AS `first_transaction_date`
          FROM (
            -- Legacy / direct entries: batch is stored on the Stock Ledger Entry itself
            SELECT `item_code`, IFNULL(`batch_no`, 'None') AS `batch_no`, `actual_qty`, `stock_uom`, `posting_date`
            FROM `tabStock Ledger Entry`
            WHERE `item_code` = %(item_code)s
              AND `is_cancelled` = 0
              AND (`serial_and_batch_bundle` IS NULL OR `serial_and_batch_bundle` = '')

            UNION ALL

            -- Bundle entries: batch + (signed) qty live in the Serial and Batch Bundle
            SELECT `sle`.`item_code`, IFNULL(`sbe`.`batch_no`, 'None') AS `batch_no`, `sbe`.`qty` AS `actual_qty`, `sle`.`stock_uom`, `sle`.`posting_date`
            FROM `tabStock Ledger Entry` AS `sle`
            INNER JOIN `tabSerial and Batch Entry` AS `sbe` ON `sbe`.`parent` = `sle`.`serial_and_batch_bundle`
            WHERE `sle`.`item_code` = %(item_code)s
              AND `sle`.`is_cancelled` = 0
              AND `sle`.`serial_and_batch_bundle` IS NOT NULL AND `sle`.`serial_and_batch_bundle` != ''
          ) AS `ledger`
          GROUP BY `batch_no`
          ORDER BY `first_transaction_date`
        ) AS `batches`
        INNER JOIN `tabBatch` ON `batches`.`batch_no` = `tabBatch`.`name`
        WHERE `qty` != 0"""
    if include_expired_disabled:
        sql_query += ";"
    else:
        sql_query += " AND (`expiry_date` IS NULL OR `expiry_date` > %(today)s) AND (`disabled` = 0);";
    data = frappe.db.sql(sql_query, {'item_code': item_code, 'today': datetime.date.today()}, as_dict=1)
    return data


@frappe.whitelist()
def set_batch_packaging_specs(batch, specs):
    if type(specs) == str:
        specs = json.loads(specs)

    packspecs =  {key: specs.get(key) for key in [
        'pallet_type', 'pallet_max_height', 'packaging_type', 'package_length', 'package_width', 'package_height', 'package_tare', 'packages_per_layer', 'layers_per_pallet'
    ]}
    packages_per_pallet = specs.get('packages_per_layer', 0) * specs.get('layers_per_pallet', 0)
    pallet_specs = {key: specs.get(key) for key in [
        'pallet_tare', 'pallet_base_height', 'pallet_length', 'pallet_width'
    ]}

    # Update pallet spec if checkbox selected
    if specs.get('update_packaging_spec'):
        packspec_doc = frappe.get_doc("Supplier Packaging Spec", specs['packaging_spec'])
        packspec_doc.update(packspecs)
        packspec_doc.packages_per_pallet = packages_per_pallet
        packspec_doc.save()
    # NOTE - Pallet type is not updated here as this has an impact on other suppliers' packaging specs and therefore seems "risky" to do from a dialog

    # Update batch data
    batch_doc = frappe.get_doc("Batch", batch)
    batch_doc.update(packspecs)
    batch_doc.update(pallet_specs)
    net_weight_per_pallet = packages_per_pallet * specs.get('package_weight', 0)
    batch_doc.update({'package_weight': specs.get('package_weight'), 'net_weight_per_pallet': net_weight_per_pallet, 'packaging_spec': specs['packaging_spec']})
    batch_doc.save()
    frappe.db.commit()


# Currently used in TDS, potentially useful elsewhere:
# Do not pull forward the attachments when canceling and amending a document
def drop_copied_attachments(doc, method=None):
    if not (doc.flags.in_insert and doc.get("amended_from")):
        return

    old_urls = {
        f.file_url
        for f in frappe.get_all(
            "File",
            filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.amended_from},
            fields=["file_url"],
        )
    }
    if not old_urls:
        return

    for f in frappe.get_all(
        "File",
        filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
        fields=["name", "file_url"],
    ):
        if f.file_url in old_urls:
            frappe.delete_doc("File", f.name, ignore_permissions=True, delete_permanently=False)


# The distinct "YYYY-MM" of the given delivery dates, ascending, as a
# comma-separated string
def get_delivery_months(delivery_dates):
    months = {getdate(d).strftime("%Y-%m") for d in delivery_dates if d}

    return ", ".join(sorted(months))


# Keep Sales Invoice.custom_delivery_months in sync with the items' delivery
# dates (they stay editable after submit)
def set_delivery_months(doc, event=None):
    delivery_months = get_delivery_months([i.get("delivery_date") for i in doc.items])

    if doc.get("custom_delivery_months") != delivery_months:
        doc.db_set("custom_delivery_months", delivery_months)
