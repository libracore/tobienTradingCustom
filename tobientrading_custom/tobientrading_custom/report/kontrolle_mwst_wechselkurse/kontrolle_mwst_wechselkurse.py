# Copyright (c) 2016-2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, getdate, nowdate

# amount columns that are summed up in the total row (exchange rates are not summable)
TOTAL_FIELDS = ["base_grand_total", "oldquery_tax", "total_taxes_and_charges", "gl_tax_amount_chf", "tax_delta_chf", "overall_tax_delta_chf"]

def execute(filters=None):
    columns, data = [], []

    if filters.quarter:
        filters.from_date, filters.end_date = get_quarter_dates(filters.quarter)
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"
    if not filters.code:
        filters.code = "200"

    # define columns
    columns = [
        {"label": _("Document"), "fieldname": "name", "fieldtype": "Dynamic Link", "options": "doctype", "width": 140},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Total"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 100},
        {"label": _("Taxes and Charges"), "fieldname": "taxes_and_charges", "fieldtype": "Data", "width": 160},
        {"label": _("Reported Tax Amount"), "fieldname": "oldquery_tax", "fieldtype": "Float", "width": 180},
        {"label": _("Document Tax Amount CHF"), "fieldname": "total_taxes_and_charges", "fieldtype": "Float", "width": 220},
        {"label": _("GL Entry Tax Amount CHF"), "fieldname": "gl_tax_amount_chf", "fieldtype": "Float", "width": 200},
        {"label": _("Tax Delta (GL - Doc) CHF"), "fieldname": "tax_delta_chf", "fieldtype": "Float", "width": 200},
        {"label": _("Tax Delta (GL - reported) CHF"), "fieldname": "overall_tax_delta_chf", "fieldtype": "Float", "width": 230},
        {"label": _("System Exchange Rate"), "fieldname": "system_exchange_rate", "fieldtype": "Float", "width": 180},
        {"label": _("Doc Exchange Rate"), "fieldname": "doc_exchange_rate", "fieldtype": "Float", "width": 160},
        {"label": _("Exchange Rate Delta"), "fieldname": "exchange_rate_delta", "fieldtype": "Float", "width": 170},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 200}
    ]

    data = get_data(filters.from_date, filters.end_date, filters.code, filters.company)
    if data:
        data.append(get_total_row(data))

    # columns, data, message, chart, report_summary, skip_total_row
    return columns, data, None, None, None, 1

def get_total_row(data):
    """ Sum up the amount columns only - summing exchange rates would be meaningless """
    total_row = {"name": _("Total"), "doctype": None, "is_total_row": 1}     # is_total_row is used by the js formatter to print it in bold
    for field in TOTAL_FIELDS:
        total_row[field] = sum([flt(d.get(field)) for d in data])

    return total_row

def get_quarters():
    """ Return all completed quarters of all fiscal years, oldest first """
    fiscal_years = frappe.get_all(
        "Fiscal Year",
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_start_date ASC")

    today = getdate(nowdate())
    quarters = []
    for fy in fiscal_years:
        if not fy.year_start_date:
            continue
        for i in range(0, 4):
            start_date = add_months(getdate(fy.year_start_date), 3 * i)
            end_date = add_days(add_months(start_date, 3), -1)
            if fy.year_end_date and end_date > getdate(fy.year_end_date):
                end_date = getdate(fy.year_end_date)
            if start_date > end_date:
                continue
            quarters.append({
                "quarter": "{fy}Q{n}".format(fy=fy.name, n=(i + 1)),
                "from_date": start_date,
                "end_date": end_date
            })

    # only offer quarters that have ended (VAT is reported per completed quarter)
    completed = [q for q in quarters if q['end_date'] < today]
    return completed or quarters

@frappe.whitelist()
def get_quarter_options():
    """ Endpoint for the report filter: options and default (latest quarter) """
    quarters = get_quarters()
    return {
        "options": [q['quarter'] for q in quarters],
        "default": quarters[-1]['quarter'] if quarters else None
    }

def get_quarter_dates(quarter):
    """ Resolve a quarter key (e.g. 2026Q2) back to from_date/end_date """
    for q in get_quarters():
        if q['quarter'] == quarter:
            return q['from_date'], q['end_date']

    frappe.throw(_("Invalid quarter: {0}").format(quarter))

def get_data(from_date, end_date, code, company="%"):
    # try to fetch data from VAT query
    if frappe.db.exists("VAT query", "viewVAT_{code}".format(code=code)):
        sql_query = ("""SELECT *,
                  ( `gl_tax_amount_chf` - `total_taxes_and_charges` ) AS `tax_delta_chf`,
                  ( IFNULL(`oldquery_tax`,`gl_tax_amount_chf`) - `total_taxes_and_charges` ) AS `overall_tax_delta_chf`,
                  IF(`doc_exchange_rate` != 0, ROUND(`doc_exchange_rate` - `system_exchange_rate`, 4), 0) AS `exchange_rate_delta`
                FROM ({query}) AS `s`
                WHERE `s`.`posting_date` >= '{start_date}'
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=frappe.get_value("VAT query", "viewVAT_{code}".format(code=code), "query"),
                start_date=from_date, end_date=end_date).replace("{company}", company))
    else:
        # fallback database view
        sql_query = """SELECT
                    *
                FROM `viewVAT_{code}`
                WHERE
                    `posting_date` >= \"{start_date}\"
                    AND `posting_date` <= \"{end_date}\"
                ORDER BY
                    `posting_date`;""".format(
                    start_date=from_date, end_date=end_date, code=code)
    try:
        data = frappe.db.sql(sql_query, as_dict = True)
    except:
        return []
    return data

# v15 wrapper for jinja/get_data (incompatible function name rewrite)
def get_tax_details(from_date, end_date, code, company="%"):
    return get_data(from_date, end_date, code, company)

# this is an endpoint for the jinja environment
def get_vat_control_details(from_date, end_date, code, company="%"):
    return get_data(from_date, end_date, code, company)
