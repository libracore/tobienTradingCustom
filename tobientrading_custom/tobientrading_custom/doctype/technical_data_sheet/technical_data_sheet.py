# Copyright (c) 2024, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TechnicalDataSheet(Document):
    pass

def get_current_tds(item_code):
    matching_tds = frappe.get_all("Technical Data Sheet", filters = {'item_code': item_code, 'docstatus': 1})
    if len(matching_tds) > 1:
        frappe.throw("Error: Several active TDS exist for Item '{0}'".format(item_code))
    elif len(matching_tds) == 0:
        return None
    else:
        return matching_tds[0].name