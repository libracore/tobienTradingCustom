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
		{"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": "Date", "fieldname": "date_coa", "fieldtype": "Date", "width": 100},
		{"label": "Batch TT", "fieldname": "batch_tt", "fieldtype": "Data", "width": 100},
		{"label": "Sample Lot TT", "fieldname": "sample_lot_tt", "fieldtype": "Data", "width": 100},
		{"label": "Batch Producer", "fieldname": "batch_producer", "fieldtype": "Data", "width": 100},
		{"label": "Certificate of Analysis", "fieldname": "coa", "fieldtype": "Link", "options": "Certificate of Analysis", "width": 100},
		{"label": "Parameter", "fieldname": "parameter", "fieldtype": "Link", "options": "Measurement Parameter", "width": 100},
		{"label": "Result", "fieldname": "result", "fieldtype": "Data", "width": 100},
		{"label": "Unit", "fieldname": "unit", "fieldtype": "Data", "width": 100},
		{"label": "Max Level", "fieldname": "max_level", "fieldtype": "Data", "width": 100},
		{"label": "Guide Value", "fieldname": "guide_value", "fieldtype": "Data", "width": 100},
		{"label": "Limit Value", "fieldname": "limit_value", "fieldtype": "Data", "width": 100},
		{"label": "Processing Factor", "fieldname": "processing_factor", "fieldtype": "Data", "width": 100},
		{"label": "Measurement Uncertainty", "fieldname": "measurement_uncertainty", "fieldtype": "Data", "width": 100},
		{"label": "EU Legislation", "fieldname": "eu_legislation", "fieldtype": "Data", "width": 100},
		{"label": "Batch Volume", "fieldname": "batch_volume", "fieldtype": "Data", "width": 100},
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

	query = """
		SELECT 
			`tabCertificate of Analysis`.`item_name` AS `item`,
			`tabCertificate of Analysis`.`date_coa`,
			`tabCertificate of Analysis`.`batch_tt`,
			`tabCertificate of Analysis`.`sample_lot_tt`,
			`tabCertificate of Analysis`.`batch_producer`,
			`tabCertificate of Analysis`.`name` AS `coa`,
			`tabCertificate of Analysis Result`.`parameter`,
			`tabCertificate of Analysis Result`.`result`,
			`tabCertificate of Analysis Result`.`unit`,
			`tabCertificate of Analysis Result`.`max_level`,
			`tabCertificate of Analysis Result`.`guide_value`,
			`tabCertificate of Analysis Result`.`limit_value`,
			"" AS `processing_factor`,
			"" AS `measurement_uncertainty`,
			"" AS `eu_legislation`,
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
def download_pdf(item, parameter, batch):
    filters = {'item': item, 'parameter': parameter, 'batch_tt': batch}

    content = frappe.render_template(
        "tobientrading_custom/tobientrading_custom/report/analysedatenbank/analysedatenbank.html", 
        {
            'data': get_data(filters),
            'filters': filters
        }
    )

    date = datetime.strptime(now(), "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")

    options = {
        "orientation": "Landscape",
        "footer-center": f"Page [page] of [topage]  |  Date: {date}  |  Item: {item}  |  Parameter: {parameter}  |  Batch: {batch}",
        "footer-font-size": "8",
    }

    pdf = get_pdf(content, options)

    frappe.local.response.filename = f"Analysedatenbank_{item}_{parameter}_{batch}_{date}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

    return

