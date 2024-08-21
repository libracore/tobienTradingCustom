# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json

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
