# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from datetime import datetime
from bs4 import BeautifulSoup

class CertificateofAnalysis(Document):
    pass

@frappe.whitelist()
def get_results(coa):
    query = """
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
    data = json.loads(data)
    data = data[1:]
    
    for row in data:
        try:
            begin_of_analysis = datetime.strptime(row[1], '%d.%m.%Y').strftime('%Y-%m-%d')
            end_of_analysis = datetime.strptime(row[2], '%d.%m.%Y').strftime('%Y-%m-%d')
            
            # Create COA if not exists
            coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": row[0]})
            if coa:
                coa = frappe.get_doc("Certificate of Analysis", coa)
            else:
                coa = frappe.new_doc("Certificate of Analysis")
                laboratory = frappe.get_doc("Supplier", "SUP-00096").name

                if row[5] == "":
                    parts = row[4].split("\r\n")
                    item_code = next((split_and_strip(part) for part in parts if part.strip().startswith("A")), None)
                    if not item_code:
                        # Try to find item code in row 3
                        item_code = split_and_strip(row[3])
                        item = frappe.db.exists("Item", item_code)
                        if not item:
                            frappe.log_error("Item code not found in row: {row}".format(row=row), "COA Import: Item code not found")
                            continue

                    batch = next((split_and_strip(part, 1) for part in parts if part.strip().lower().startswith("lot:")), None)
                else:
                    item_code = split_and_strip(row[4])
                    batch = split_and_strip(row[5], 1)

                item = frappe.get_doc("Item", item_code)

                if frappe.db.exists("Batch", batch):
                    batch_tt = batch
                else:
                    batch_tt = ""
                    frappe.log_error("Batch {batch} not found in row {row}".format(batch=batch, row=row), "COA Import: Batch not found")
                
                coa.update({
                    "certificate_of_analysis": row[0],
                    "item": item_code,
                    "item_name": item.item_name,
                    "item_group": item.item_group,
                    "date_coa": end_of_analysis,
                    "begin_of_analysis": begin_of_analysis,
                    "end_of_analysis": end_of_analysis,
                    "laboratory": "SUP-00096",
                    "batch_tt": batch_tt
                })
            
            coa.save()

            # Create COA result if parameter, result, and unit are available
            if row[7] and row[8] and row[9] and row[8] != "\xa0":
                parameter_name = row[7].strip()

                if "<" in parameter_name or ">" in parameter_name:
                    parameter_name = parameter_name.replace("<", "").replace(">", "")
                parameter = frappe.db.exists("Measurement Parameter", parameter_name)
                if parameter:
                    parameter = frappe.get_doc("Measurement Parameter", parameter_name)
                else:
                    parameter = frappe.new_doc("Measurement Parameter")
                    parameter.parameter = parameter_name
                    parameter.save()

                coa_result = frappe.db.exists("Certificate of Analysis Result", {"coa": coa.name, "parameter": parameter_name})

                if not coa_result:
                    coa_result = frappe.new_doc("Certificate of Analysis Result")
                    coa_result.update({
                        "parameter": parameter_name, 
                        "test_type": parameter.test_type,
                        "coa": coa.name,
                        "coa_date": end_of_analysis,
                        "result": row[8],
                        "unit": row[9],
                        "max_level": row[10]
                    })
                    
                    coa_result.save()
                    coa.save()
        except Exception as e:
            frappe.log_error("Error while creating COA for row {row} from Excel data: {error}".format(row=row, error=e), "COA Import")
            continue

    return "COA created. Check logs for potential errors."

def split_and_strip(string, idx=0):
    return string.split()[idx].strip()
