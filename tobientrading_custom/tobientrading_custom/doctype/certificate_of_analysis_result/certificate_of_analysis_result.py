# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CertificateofAnalysisResult(Document):
	pass

@frappe.whitelist()
def get_test_type_and_subcategory(parameter):
	query = """
		SELECT `test_type`, `subcategory`
		FROM `tabMeasurement Parameter`
		WHERE `parameter` = '{parameter}'
	""".format(parameter=parameter)

	results = frappe.db.sql(query, as_dict=True)
	return results