# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns, data = [], []
    
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"
    if not filters.code:
        filters.code = "200"

    # define columns
    columns = [
        {"label": _("Code"), "fieldname": "code", "fieldtype": "Data", "width": 80},
        {"label": _("Document"), "fieldname": "name", "fieldtype": "Dynamic Link", "options": "doctype", "width": 120},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Total"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 100},
        {"label": _("Taxes and Charges"), "fieldname": "taxes_and_charges", "fieldtype": "Data", "width": 150},
        {"label": _("Tax Amount"), "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 100},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150}
    ]

    data = get_data(filters.from_date, filters.end_date, filters.company)
    return columns, data

def get_data(from_date, end_date, company="%"):
    data = []
    
    vat_queries = frappe.db.sql("""
        SELECT `name`, `code`, `query`
        FROM `tabVAT query`
        ORDER BY `tabVAT query`.`name` ASC;""", as_dict=True)
    
    for q in vat_queries:

        sql_query = ("""SELECT *, "{code}" AS `code`
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=q['query' ],
                start_date=from_date, 
                end_date=end_date,
                code=q['code']).replace("{company}", company))      

        _data = frappe.db.sql(sql_query, as_dict = True)
        for d in _data:
            data.append(d)
                
    return data
