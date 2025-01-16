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
               `coar`.`test_type_subcategory`,
               `coar`.`parameter`, 
               `coar`.`result`,
               `coar`.`unit`,
               `coar`.`limit_value`,
               `coar`.`name`
        FROM `tabCertificate of Analysis Result` AS `coar`
        WHERE `coar`.`coa` = '{coa}'
        ORDER BY `coar`.`test_type`, `coar`.`test_type_subcategory`, `coar`.`parameter` ASC
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

            # Get item code and batch
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
                batch_doc = frappe.get_doc("Batch", batch)
                batch_tt = batch_doc.name
                batch_supplier = batch_doc.supplier_batch_number
            else:
                batch_tt = ""
                batch_supplier = ""
                frappe.log_error("Batch {batch} not found in row {row}".format(batch=batch, row=row), "COA Import: Batch not found")
            
            # Create COA if not exists
            coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": row[0]})
            if coa:
                coa = frappe.get_doc("Certificate of Analysis", coa)
            else:
                coa = frappe.new_doc("Certificate of Analysis")
                laboratory = frappe.get_doc("Supplier", "SUP-00096").name
                
                coa.update({
                    "certificate_of_analysis": row[0],
                    "item": item_code,
                    "item_name": item.item_name,
                    "item_group": item.item_group,
                    "date_coa": end_of_analysis,
                    "begin_of_analysis": begin_of_analysis,
                    "end_of_analysis": end_of_analysis,
                    "laboratory": "SUP-00096",
                    "batch_tt": batch_tt,
                    "batch_producer": batch_supplier
                })
            
            coa.save()

            # Create COA result if parameter, result, and unit are available
            if row[7] and row[8] and row[9] and row[8] != "\xa0":
                parameter_name = row[7].strip()

                if "<" in parameter_name or ">" in parameter_name:
                    parameter_name = parameter_name.replace("<", "≤").replace(">", "≥")
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
                        "test_type_subcategory": parameter.subcategory,
                        "coa": coa.name,
                        "coa_date": end_of_analysis,
                        "item": item_code,
                        "batch_tt": batch_tt,
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

@frappe.whitelist()
def create_coa_from_xml_data(data):
    try:
        soup = BeautifulSoup(data, 'xml')

        for group in soup.find_all('Groep1'):
            try:
                certificate_of_analysis = group.find('sample_sample_number').text
                report_date = group.find('ReportDate').text
                begin_of_analysis = datetime.strptime(report_date, '%d-%m-%YT%H:%M:%S').strftime('%Y-%m-%d')
                end_of_analysis = datetime.strptime(report_date, '%d-%m-%YT%H:%M:%S').strftime('%Y-%m-%d')
                item_code = group.find('Referencenumber').text
                batch = group.find('BatchNumberSuppliers').text

                if frappe.db.exists("Batch", batch):
                    batch_doc = frappe.get_doc("Batch", batch)
                    batch_tt = batch_doc.name
                    batch_supplier = batch_doc.supplier_batch_number
                else:
                    batch_tt = ""
                    batch_supplier = ""
                    frappe.log_error("Batch {batch} not found".format(batch=batch), "COA Import: Batch not found")

                for parameter in group.find_all('Parameter'):
                    try:
                        # Extract parameter details
                        parameter_name = parameter.find('component_name').text if parameter.find('component_name') else None
                        result = parameter.find('result_entry').text if parameter.find('result_entry') else None
                        unit = parameter.find('units_1_display_string').text if parameter.find('units_1_display_string') else None
                        max_level = parameter.find('Detectionlimit').text if parameter.find('Detectionlimit') else None

                        # Ensure item exists in the system
                        item = frappe.get_doc("Item", item_code)

                        # Create or fetch the COA document
                        coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": certificate_of_analysis})
                        if coa:
                            coa = frappe.get_doc("Certificate of Analysis", coa)
                        else:
                            coa = frappe.new_doc("Certificate of Analysis")
                            coa.update({
                                "certificate_of_analysis": certificate_of_analysis,
                                "item": item_code,
                                "item_name": item.item_name,
                                "item_group": item.item_group,
                                "date_coa": end_of_analysis,
                                "begin_of_analysis": begin_of_analysis,
                                "end_of_analysis": end_of_analysis,
                                "laboratory": "SUP-00381",
                                "batch_tt": batch_tt,
                            })
                        coa.save()

                        # Only create a COA result if required values are available
                        if parameter_name and result and unit:
                            # Create or fetch the Measurement Parameter
                            parameter_doc = frappe.db.exists("Measurement Parameter", parameter_name)
                            if not parameter_doc:
                                parameter_doc = frappe.new_doc("Measurement Parameter")
                                parameter_doc.parameter = parameter_name
                                parameter_doc.save()

                            # Check if the COA result already exists
                            coa_result = frappe.db.exists("Certificate of Analysis Result", {"coa": coa.name, "parameter": parameter_name})
                            if not coa_result:
                                coa_result = frappe.new_doc("Certificate of Analysis Result")
                                coa_result.update({
                                    "parameter": parameter_name,
                                    "coa": coa.name,
                                    "result": result,
                                    "unit": unit,
                                    "max_level": max_level
                                })
                                coa_result.save()

                    except Exception as e:
                        frappe.log_error(f"Error while processing parameter in group {group}: {str(e)}", "COA Import - Parameter Error")
                        continue 

            except Exception as e:
                frappe.log_error(f"Error while processing group {group}: {str(e)}", "COA Import - Group Error")
                continue 

        return "COA created from XML. Check logs for potential errors."

    except Exception as e:
        frappe.log_error(f"Error parsing XML data: {str(e)}", "COA Import - XML Parsing Error")
        return "Error parsing XML data."

def split_and_strip(string, idx=0):
    return string.split()[idx].strip()