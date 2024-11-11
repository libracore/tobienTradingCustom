# Copyright (c) 2024, vanessa bualat and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CertificateofAnalysis(Document):
	pass

@frappe.whitelist()
def get_results(coa):
	query="""
		SELECT `coar`.`test_type`,
			`coar`.`parameter`, 
			`coar`.`result`,
			`coar`.`unit`,
			`coar`.`name`
		FROM `tabCertificate of Analysis Result` AS `coar`
		WHERE `coar`.`coa` = '{coa}'
		ORDER BY `coar`.`test_type`, `coar`.`parameter` ASC
		""".format(coa=coa)

	results = frappe.db.sql(query, as_dict=True)
	results_html = frappe.render_template("tobientrading_custom/templates/includes/coa_results.html", {"results": results})
	return results_html

@frappe.whitelist()
def create_coa_from_excel_data(data):
	data = data[1:]
	for row in data:
		coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": row[0]})
		if coa:
			coa = frappe.get_doc("Certificate of Analysis", coa)
		else:
			coa = frappe.new_doc("Certificate of Analysis")
			laboratory = frappe.get_doc("Laboratory", "SUP-00096")
			item_code = row[4].split("\r\n")[1]
			lot_tt = row[4].split("\r\n")[0]
			item = frappe.get_doc("Item", item_code)
			coa.update({
				"item_code": item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"date_coa": row[2],
				"begin_of_analysis": row[1],
				"end_of_analysis": row[2],
				"sample_lot_tt": lot_tt,
				"laboratory": laboratory
			})
		coa.save()
		#create coa result
		if row[7] and row[8] and row[9]:
			coa_result = frappe.new_doc("Certificate of Analysis Result")
			coa_result.update({
				"parameter": row[7],
				"coa": coa.name,
				"coa_date": row[2],
				"result": row[8],
				"unit": row[9],
				"max_level": row[10]
			})
			coa_result.save()
			coa.save()
	return "COA created successfully"