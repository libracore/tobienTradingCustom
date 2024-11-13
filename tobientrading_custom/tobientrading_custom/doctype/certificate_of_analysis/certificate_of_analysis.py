# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from datetime import datetime

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
            
            #create COA if not exists
            coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": row[0]})
            if coa:
                coa = frappe.get_doc("Certificate of Analysis", coa)
            else:
                coa = frappe.new_doc("Certificate of Analysis")
                laboratory = frappe.get_doc("Supplier", "SUP-00096").name
                if row[5]=="":
                    parts = row[4].split("\r\n")
                    if len(parts) == 1:
                        frappe.log_error("Item code not found in row: {row}".format(row=row), "COA Import")
                        continue
                    if parts[0].strip().startswith("A"):
                        item_code = parts[0].split[0].strip()
                    elif parts[1].strip().startswith("A"):
                        item_code = parts[1].split[0].strip()
                    elif len(parts) == 3 and parts[2].strip().startswith("A"):
                        item_code = parts[2].split[0].strip()
                    else:
                        item_code = row[3].split()[0].strip()
                else:
                    item_code = row[4].split[0].strip()

                item = frappe.get_doc("Item", item_code)
                
                coa.update({
                    "certificate_of_analysis": row[0],
                    "item": item_code,
                    "item_name": item.item_name,
                    "item_group": item.item_group,
                    "date_coa": end_of_analysis,
                    "begin_of_analysis": begin_of_analysis,
                    "end_of_analysis": end_of_analysis,
                    "laboratory": "SUP-00096"
                })
            
            coa.save()

            # Create COA result if parameter, result and unit are available
            if row[7] and row[8] and row[9]:
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
                
                coa_result = frappe.new_doc("Certificate of Analysis Result")
                coa_result.update({
                    "parameter": parameter_name, 
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
    return "COA created successfully"