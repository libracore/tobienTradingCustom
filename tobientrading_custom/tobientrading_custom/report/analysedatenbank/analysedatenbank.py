# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.utils.pdf import get_pdf
from datetime import datetime

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 80},
		{"label": "Date", "fieldname": "date_coa", "fieldtype": "Date", "width": 100},
		{"label": "Batch TT", "fieldname": "batch_tt", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"label": "Supplier Batch Number", "fieldname": "supplier_batch_number", "fieldtype": "Data", "width": 100},
		{"label": "Certificate of Analysis", "fieldname": "coa", "fieldtype": "Link", "options": "Certificate of Analysis", "width": 100},
		{"label": "Parameter", "fieldname": "parameter", "fieldtype": "Link", "options": "Measurement Parameter", "width": 100},
		{"label": "Result", "fieldname": "result", "fieldtype": "Data", "width": 100},
		{"label": "Unit", "fieldname": "unit", "fieldtype": "Data", "width": 100},
		{"label": "Max Level", "fieldname": "max_level", "fieldtype": "Data", "width": 100},
		{"label": "Guide Value", "fieldname": "guide_value", "fieldtype": "Data", "width": 100},
		{"label": "Limit Value", "fieldname": "limit_value", "fieldtype": "Data", "width": 100},
		{"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 100},
		{"label": "Test Type", "fieldname": "test_type", "fieldtype": "Data", "width": 100},
		{"label": "Subcategory", "fieldname": "subcategory_name", "fieldtype": "Data", "width": 100},
		{"label": "Method", "fieldname": "method", "fieldtype": "Data", "width": 100}
	]

	return columns

def get_data(filters):
	conditions = ""
	if filters.get("item"):
		conditions += " AND `tabCertificate of Analysis`.`item` = '{0}'".format(filters.get("item"))
	if filters.get("parameter"):
		conditions += " AND `tabCertificate of Analysis Result`.`parameter` = '{0}'".format(filters.get("parameter"))
	if filters.get("batch_tt"):
		conditions += " AND `tabCertificate of Analysis`.`batch_tt` = '{0}'".format(filters.get("batch_tt"))
	if filters.get("item_group"):
		conditions += " AND `tabCertificate of Analysis`.`item_group` = '{0}'".format(filters.get("item_group"))
	if filters.get("test_type"):
		conditions += " AND `tabCertificate of Analysis Result`.`test_type` = '{0}'".format(filters.get("test_type"))
	if filters.get("subcategory"):
		conditions += " AND `tabMeasurement Parameter`.`subcategory_name` = '{0}'".format(filters.get("subcategory"))

	query = """
		SELECT 
			`tabCertificate of Analysis`.`item` AS `item`,
			`tabCertificate of Analysis`.`item_name` AS `item_name`,
			`tabCertificate of Analysis`.`date_coa`,
			`tabCertificate of Analysis`.`batch_tt`,
			`tabCertificate of Analysis`.`sample_lot_tt`,
			`tabCertificate of Analysis`.`supplier_batch_number`,
			`tabCertificate of Analysis`.`name` AS `coa`,
			`tabCertificate of Analysis Result`.`parameter`,
			`tabCertificate of Analysis Result`.`result`,
			`tabCertificate of Analysis Result`.`unit`,
			`tabCertificate of Analysis Result`.`max_level`,
			`tabCertificate of Analysis Result`.`guide_value`,
			`tabCertificate of Analysis Result`.`limit_value`,
			`tabCertificate of Analysis`.`batch_volume`,
			`tabCertificate of Analysis`.`item_group`,
			`tabCertificate of Analysis Result`.`test_type`,
			`tabMeasurement Parameter`.`subcategory_name`,
			`tabCertificate of Analysis Result`.`method`
		FROM `tabCertificate of Analysis`
		LEFT JOIN `tabCertificate of Analysis Result` 
			ON `tabCertificate of Analysis`.`name` = `tabCertificate of Analysis Result`.`coa`
		LEFT JOIN `tabMeasurement Parameter`
			ON `tabCertificate of Analysis Result`.`parameter` = `tabMeasurement Parameter`.`name`
		WHERE `tabCertificate of Analysis Result`.`parameter` IS NOT NULL
		{conditions}
		ORDER BY `tabCertificate of Analysis`.`item_name`, 
				`tabCertificate of Analysis`.`date_coa`, 
				`tabCertificate of Analysis Result`.`parameter` ASC
	""".format(conditions=conditions)

	data = frappe.db.sql(query, as_dict=True)
	return data

@frappe.whitelist()
def download_pdf(item, parameter, batch, item_group, test_type, subcategory, supplier_batch_number=None):
    filters = {'item': item, 'parameter': parameter, 'batch_tt': batch, 'item_group': item_group, 'test_type': test_type, 'subcategory': subcategory}
    options = {'supplier_batch_number': supplier_batch_number, **filters}

    content = frappe.render_template(
		"tobientrading_custom/tobientrading_custom/report/analysedatenbank/analysedatenbank.html", 
		{
			'data': get_data(filters),
			'options': options
		}
	)

    date = datetime.strptime(now(), "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")

    footer_parts = [
		"Page [page] of [topage]",
		f"Date: {date}",
		f"Item: {item}" if item else "",
		f"Parameter: {parameter}" if parameter else "",
		f"Batch: {batch}" if batch else "",
		f"Item Group: {item_group}" if item_group else "",
		f"Test Type: {test_type}" if test_type else "",
		f"Subcategory: {subcategory}" if subcategory else ""
	]

    footer_center = " | ".join(part for part in footer_parts if part)

    options = {
		"orientation": "Landscape",
		"footer-center": footer_center,
		"footer-font-size": "8"
	}

    pdf = get_pdf(content, options)

    filename_parts = ["Analysedatenbank"]
    if item:
	    filename_parts.append(item)
    if parameter:
	    filename_parts.append(parameter)
    if batch:
	    filename_parts.append(batch)
    if item_group:
	    filename_parts.append(item_group)
    if test_type:
	    filename_parts.append(test_type)
    if subcategory:
	    filename_parts.append(subcategory)
    filename_parts.append(date)

    frappe.local.response.filename = f"{'_'.join(filename_parts)}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

    return

