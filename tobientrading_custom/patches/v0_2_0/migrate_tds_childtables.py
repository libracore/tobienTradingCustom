# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt
import frappe
from frappe import _

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
    
def execute():
    # make sure new structures are loaded
    print("Load doctypes...")
    for source, destination in table_map.items():
        load_structure(destination)
    
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
    for source, destination in table_map.items():
        print("...{0} to {1}".format(source, destination))
        copy_table(source, destination)
    
    print("Moving TDS child tables into app done. 🚀🚀🚀")

def load_structure(table):   
    try:
        frappe.reload_doc("tobientrading_custom", "doctype", table)
    except Exception as err:
        print("{0}".format(err))
    return
    
def copy_table(source, destination):
    try:
        destination_fields = []
        for f in frappe.db.sql("""DESCRIBE `tab{destination}`;""".format(destination=destination), as_dict=True):
            destination_fields.append(f.get('Field'))
            
        frappe.db.sql("""
            INSERT INTO `tab{destination}` 
            ({fields})
            SELECT {fields} FROM `tab{source}`;""".format(
                source=source, 
                destination=destination,
                fields="`" + "`, `".join(destination_fields) + "`"
            )
        )
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
