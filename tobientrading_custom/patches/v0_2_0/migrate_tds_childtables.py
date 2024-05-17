# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute():
    # make sure new structures are loaded
    print("Load doctypes...")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Origin")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Certificate")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet MSDS")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Customs Tariff")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Sensoric Parameter")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Physical and Chemical Parameter")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Nutritional Information")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Microbiologiacal Properties")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Allergene")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Packaging and Storage")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Additional Packaging and Storage")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Dietary Information")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Heavy Metal")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Foreign Body")
    frappe.reload_doc("tobientrading_custom", "doctype", "Technical Data Sheet Additional Information")
    
    # clean up deprecated columns (these were removed but are still in the DB)
    drop_deprecated_column("Allergene Table", "allergene")
    drop_deprecated_column("Allergene Table", "absent")
    drop_deprecated_column("Allergene Table", "present")
    drop_deprecated_column("Allergene Table", "crosscontaamination")
    drop_deprecated_column("Packaging and Storage Table II", "_user_tags")
    drop_deprecated_column("Packaging and Storage Table II", "_comments")
    drop_deprecated_column("Packaging and Storage Table II", "_assign")
    drop_deprecated_column("Packaging and Storage Table II", "_liked_by")

    # copy column data
    print("Copy column data...")
    frappe.db.sql("""UPDATE `tabTechnical Data Sheet` SET `item_code` = `product_no`;""")
    
    # copy child tables
    print("Copy child tables...")
    table_map = {
        "Origins": "Technical Data Sheet Origin",
        "TDS Certificate Table": "Technical Data Sheet Certificate",
        "MSDS Table": "Technical Data Sheet MSDS",
        "Customs Tariff Table": "Technical Data Sheet Customs Tariff",
        "Sensoric Parameter Table": "Technical Data Sheet Sensoric Parameter",
        "Physical and Chemical Parameter Table": "Technical Data Sheet Physical and Chemical Parameter",
        "Nutritional Information Table": "Technical Data Sheet Nutritional Information",
        "Microbiologiacal Propertie Table": "Technical Data Sheet Microbiologiacal Properties",
        "Allergene Table": "Technical Data Sheet Allergene",
        "Packaging and Storage Table": "Technical Data Sheet Packaging and Storage",
        "Packaging and Storage Table II": "Technical Data Sheet Additional Packaging and Storage",
        "Dietary Information Table": "Technical Data Sheet Dietary Information",
        "Heavy Metal Table": "Technical Data Sheet Heavy Metal",
        "Foreign Body Table": "Technical Data Sheet Foreign Body",
        "Additional Information Table": "Technical Data Sheet Additional Information"
    }
    for source, destination in table_map.items():
        print("...{0} to {1}".format(source, destination))
        copy_table(source, destination)
    
    print("Moving TDS child tables into app done. 🚀🚀🚀")

def copy_table(source, destination):
    try:
        frappe.db.sql("""INSERT INTO `tab{destination}` 
                     SELECT * FROM `tab{source}`;""".format(source=source, destination=destination))
        frappe.db.commit()
    except Exception as err:
        print("{0}".format(err))
    return

def drop_deprecated_column(table, column):
    try:
        frappe.db.sql("""ALTER TABLE `tab{table}` DROP COLUMN `{column}`;""".format(table=table, column=column))
        frappe.db.commit()
    except Exception as err:
        print("{0}".format(err))
    return
