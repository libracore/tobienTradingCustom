# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.attach_pdf import attach_pdf

class TechnicalDataSheet(Document):
    def on_submit(self):
        self.update_items()
        self.attach_pdf()
        return
        
    def update_items(self):
        # update all items that were linked to the previous version with the current version
        if self.amended_from:
            items = frappe.get_all("Item", filters={'technical_data_sheet': self.amended_from}, fields=['name'])
            
            for i in items:
                frappe.db.set_value("Item", i['name'], 'technical_data_sheet', self.name)
                
            frappe.db.commit()
        
        return
        
    def attach_pdf(self):
        attach_pdf(doctype=self.doctype, docname=self.name)
        return
