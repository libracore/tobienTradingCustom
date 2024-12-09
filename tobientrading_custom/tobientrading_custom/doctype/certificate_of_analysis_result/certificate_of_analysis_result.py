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

def update_test_type_and_subcategory(doc, method):
    new_test_type = doc.test_type
    new_subcategory = doc.subcategory

    coas_to_update = frappe.get_all("Certificate of Analysis Result", filters={"parameter": doc.parameter}, fields=["name"])

    for coa in coas_to_update:
        coa = frappe.get_doc("Certificate of Analysis Result", coa.name)
        coa.test_type = new_test_type
        coa.test_type_subcategory = new_subcategory
        coa.save()