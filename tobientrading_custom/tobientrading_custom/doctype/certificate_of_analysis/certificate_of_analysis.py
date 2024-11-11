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
