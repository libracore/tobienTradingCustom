# Copyright (c) 2024, vanessa bualat and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CertificateofAnalysis(Document):
	pass


@frappe.whitelist()
def get_results(coa):
	query="""
		SELECT `coar`.`parameter`, 
			`coar`.`result`,
			`coar`.`unit`
		FROM `tabCertificate of Analysis Result` AS `coar`
		WHERE `coar`.`coa` = '{coa}'
		""".format(coa=coa)

	results = frappe.db.sql(query, as_dict=True)
	return results