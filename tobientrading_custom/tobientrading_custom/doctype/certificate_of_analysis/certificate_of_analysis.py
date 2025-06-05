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
               `mp`.`subcategory_name`,
               `coar`.`parameter`, 
               `coar`.`result`,
               `coar`.`unit`,
               `coar`.`max_level`,
               `coar`.`guide_value`,
               `coar`.`limit_value`,
               `coar`.`name`
        FROM `tabCertificate of Analysis Result` AS `coar`
        LEFT JOIN `tabMeasurement Parameter` AS `mp` ON `coar`.`parameter` = `mp`.`name`
        WHERE `coar`.`coa` = '{coa}'
        ORDER BY `coar`.`test_type`, `mp`.`subcategory_name`, `coar`.`parameter` ASC
    """.format(coa=coa)

    results = frappe.db.sql(query, as_dict=True)
    results_html = frappe.render_template("tobientrading_custom/templates/includes/coa_results.html", {"results": results})
    return results_html

@frappe.whitelist()
def create_coa_from_excel_data(data):    
    data = json.loads(data)[1:]
    
    for row in data:
        try:
            # get COA details
            begin_of_analysis = format_date(row[1])
            end_of_analysis = format_date(row[2])
            item_code, batch = row[4], row[5]

            item = frappe.get_doc("Item", item_code)

            batch_tt, batch_supplier = fetch_batch_details(batch)
            
            certficate_of_analysis = create_and_fetch_coa(row[0], item_code, item.item_name, item.item_group, end_of_analysis, begin_of_analysis, "SUP-00096", batch_tt, batch_supplier)

            # create COA result if parameter, result, and unit are available
            if row[8] and row[9] and row[9] != "\xa0":
                parameter_name = row[8].strip()
                if "<" in parameter_name or ">" in parameter_name:
                    parameter_name = parameter_name.replace("<", "≤").replace(">", "≥")

                parameter = create_or_fetch_parameter(parameter_name)
                result = row[9]
                unit = safe_get(row, 10)
                max_level = safe_get(row, 11)
                method = safe_get(row, 14)
                guide_value = safe_get(row, 12)
                limit_value = safe_get(row, 13)
                assessment = row[7]
                create_coa_result(certficate_of_analysis, parameter, end_of_analysis, item_code, batch_tt, result, unit, max_level, method, guide_value, limit_value, assessment)

        except Exception as e:
            frappe.log_error("Error while creating COA for row {row} from Excel data: {error}".format(row=row, error=e), "COA Import")

    return "COA created from Excel. Check logs for potential errors."

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

                batch_tt, batch_supplier = fetch_batch_details(batch)

                for parameter in group.find_all('Parameter'):
                    try:
                        parameter_name = parameter.find('component_name').text if parameter.find('component_name') else None
                        result = parameter.find('result_entry').text if parameter.find('result_entry') else None
                        unit = parameter.find('units_1_display_string').text if parameter.find('units_1_display_string') else None
                        max_level = parameter.find('Detectionlimit').text if parameter.find('Detectionlimit') else None

                        item = frappe.get_doc("Item", item_code)

                        coa = create_and_fetch_coa(certificate_of_analysis, item_code, item.item_name, item.item_group, end_of_analysis, begin_of_analysis, "SUP-00381", batch_tt, batch_supplier)

                        # create COA result if parameter, result, and unit are available
                        if parameter_name and result:
                            parameter = create_or_fetch_parameter(parameter_name)
                            create_coa_result(coa, parameter, end_of_analysis, item_code, batch_tt, result, unit, max_level)

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

# helper functions
def split_and_strip(string, idx=0):
    return string.split()[idx].strip()

def format_date(date):
    return datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d')

def safe_get(lst, index, default=""):
    try:
        return lst[index]
    except IndexError:
        return default

# functions to parse coa details
def parse_item_and_batch(row):
    if row[5] == "":
        parts = row[4].split("\r\n")
        item_code = next((split_and_strip(part) for part in parts if part.strip().startswith("A")), None)
        if not item_code:
            # Try to find item code in row 3
            item_code = split_and_strip(row[3])
            item = frappe.db.exists("Item", item_code)
            if not item:
                frappe.log_error("Item code not found in row: {row}".format(row=row), "COA Import: Item code not found")

        batch = next((split_and_strip(part, 1) for part in parts if part.strip().lower().startswith("lot:")), None)
    else:
        item_code = split_and_strip(row[4])
        batch = split_and_strip(row[5], 1)

    return item_code, batch

def fetch_batch_details(batch):
    #remove 'LOT: ' from batch and remove breaklines
    batch = batch.replace("LOT: ", "").replace("\r\n", "")
    if frappe.db.exists("Batch", batch):
        batch_doc = frappe.get_doc("Batch", batch)
        batch_tt = batch_doc.name
        batch_supplier = batch_doc.supplier_batch_number
    else:
        batch_tt = ""
        batch_supplier = ""
        frappe.log_error("Batch {batch} not found.".format(batch=batch), "COA Import: Batch not found")
    
    return batch_tt, batch_supplier

# functions to create docs
def create_and_fetch_coa(certificate_of_analysis, item_code, item_name, item_group, end_of_analysis, begin_of_analysis, laboratory, batch_tt, batch_supplier):
    coa = frappe.db.exists("Certificate of Analysis", {"certificate_of_analysis": certificate_of_analysis})
    if coa:
        coa = frappe.get_doc("Certificate of Analysis", coa)
    else:
        coa = frappe.new_doc("Certificate of Analysis")
        laboratory = frappe.get_doc("Supplier", laboratory).name
        coa.update({
            "certificate_of_analysis": certificate_of_analysis,
            "item": item_code,
            "item_name": item_name,
            "item_group": item_group,
            "date_coa": end_of_analysis,
            "begin_of_analysis": begin_of_analysis,
            "end_of_analysis": end_of_analysis,
            "laboratory": laboratory,
            "batch_tt": batch_tt,
            "supplier_batch_number": batch_supplier #TODO aj 05.06.2025 adjust this to be taken from batch
        })
    coa.save()
    
    return coa

def create_or_fetch_parameter(parameter_name):
    parameter = frappe.db.exists("Measurement Parameter", parameter_name)
    if parameter:
        parameter = frappe.get_doc("Measurement Parameter", parameter_name)
    else:
        parameter = frappe.new_doc("Measurement Parameter")
        parameter.parameter = parameter_name
        parameter.save()

    return parameter

def create_coa_result(coa, parameter, end_of_analysis, item_code, batch_tt, result, unit, max_level, method=None, guide_value=None, limit_value=None, assessment=None):
    coa_result = frappe.db.exists("Certificate of Analysis Result", {"coa": coa.name, "parameter": parameter.name})

    if not coa_result:
        coa_result = frappe.new_doc("Certificate of Analysis Result")
        coa_result.update({
            "parameter": parameter.name, 
            "test_type": parameter.test_type,
            "test_type_subcategory": parameter.subcategory,
            "test_type_subcategory_name": parameter.subcategory_name,
            "coa": coa.name,
            "coa_date": end_of_analysis,
            "item": item_code,
            "batch_tt": batch_tt,
            "method": method,
            "result": result,
            "unit": unit,
            "max_level": max_level,
            "guide_value": guide_value,
            "limit_value": limit_value,
            "assessment": assessment
        })
        
        coa_result.save()
        coa.save()