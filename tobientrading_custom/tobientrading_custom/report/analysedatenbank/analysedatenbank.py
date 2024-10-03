# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe


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
		{"label": "Legal Limit", "fieldname": "legal_limit", "fieldtype": "Data", "width": 100},
		{"label": "Legal Limit Unit", "fieldname": "legal_limit_unit", "fieldtype": "Data", "width": 100},
		{"label": "Processing Factor", "fieldname": "processing_factor", "fieldtype": "Data", "width": 100},
		{"label": "Measurement Uncertainty", "fieldname": "measurement_uncertainty", "fieldtype": "Data", "width": 100},
		{"label": "EU Legislation", "fieldname": "eu_legislation", "fieldtype": "Data", "width": 100},
		{"label": "Batch Volume", "fieldname": "batch_volume", "fieldtype": "Data", "width": 100},
		{"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 100},
		{"label": "Test Type", "fieldname": "test_type", "fieldtype": "Data", "width": 100},
		{"label": "Method", "fieldname": "method", "fieldtype": "Data", "width": 100}
	]

	return columns

def get_data(filters):
	conditions = ""
	if filters.get("item"):
		conditions += " AND `tabCertificate of Analysis`.`item_name` = '{0}'".format(filters.get("item"))
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
			COALESCE(`tabCertificate of Analysis Result`.`limit_value`, `tabCertificate of Analysis Result`.`max_level`) AS `legal_limit`,
			`tabCertificate of Analysis Result`.`unit` AS `legal_limit_unit`,
			"" AS `processing_factor`,
			"" AS `measurement_uncertainty`,
			"" AS `eu_legislation`,
			`tabCertificate of Analysis`.`batch_volume`,
			`tabCertificate of Analysis`.`item_group`,
			`tabCertificate of Analysis Result`.`test_type`,
			`tabCertificate of Analysis Result`.`method`
		FROM `tabCertificate of Analysis`
		LEFT JOIN `tabCertificate of Analysis Result` 
			ON `tabCertificate of Analysis`.`name` = `tabCertificate of Analysis Result`.`coa`
		WHERE `tabCertificate of Analysis Result`.`parameter` IS NOT NULL
		{conditions}
		ORDER BY `tabCertificate of Analysis`.`item_name`, 
				`tabCertificate of Analysis`.`date_coa`, 
				`tabCertificate of Analysis Result`.`parameter` ASC
	""".format(conditions=conditions)
	data = frappe.db.sql(query, as_dict=True)
	return data
