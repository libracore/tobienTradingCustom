# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
import frappe
from frappe import _

    
def execute():
    sql_query = """
    INSERT INTO `tabComment` (
        name, 
        comment_type, 
        content, 
        comment_by, 
        modified_by, 
        owner, 
        comment_email, 
        reference_doctype, 
        reference_name, 
        creation, 
        modified
    ) 
    SELECT  
        CONCAT('crm_note_',name) AS name,   
        'Comment' AS comment_type,
        note AS content,     
        modified_by AS comment_by, 
        modified_by, 
        owner,    
        owner AS comment_email,      
        parenttype AS reference_doctype,    
        parent AS reference_name,     
        modified AS creation,     
        modified 
    FROM `tabCRM Note`; """
    
    frappe.db.sql(sql_query)
    
    print("Moving CRM Notes to Comments done.")
