# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Excel report attached to a Swiss VAT Declaration (erpnextswiss) on submit.
#
# It freezes, at the moment of submission, the numbers of the declaration
# next to the "Kontrolle MwSt" report (the same VAT queries the declaration
# reads its values from), together with the version and text of every VAT
# query used. This way a filed declaration can always be explained later,
# even after the VAT queries or the underlying documents have changed.

from io import BytesIO

import frappe
from frappe import _
from frappe.utils import now_datetime, format_datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from erpnextswiss.erpnextswiss.attach_pdf import create_folder

# code -> list of (declaration field, measure, rate field or None)
# measure "total" = sum of base_grand_total, "tax" = sum of total_taxes_and_charges
# (exactly what vat_declaration.js get_total / get_tax use)
CODES = [
    ("200", [("total_revenue", "total", None)]),
    ("220", [("tax_free_services", "total", None)]),
    ("221", [("revenue_abroad", "total", None)]),
    ("225", [("transfers", "total", None)]),
    ("230", [("non_taxable_services", "total", None)]),
    ("235", [("losses", "total", None)]),
    ("302", [("normal_amount", "total", "normal_rate")]),
    ("303", [("normal_amount_2024", "total", "normal_rate_2024")]),
    ("312", [("reduced_amount", "total", "reduced_rate")]),
    ("313", [("reduced_amount_2024", "total", "reduced_rate_2024")]),
    ("342", [("lodging_amount", "total", "lodging_rate")]),
    ("343", [("lodging_amount_2024", "total", "lodging_rate_2024")]),
    ("322", [("amount_1", "total", "rate_1")]),
    ("323", [("amount_1_2024", "total", "rate_1_2024")]),
    ("332", [("amount_2", "total", "rate_2")]),
    ("333", [("amount_2_2024", "total", "rate_2_2024")]),
    ("382", [("additional_amount", "total", None), ("additional_tax", "tax", None)]),
    ("383", [("additional_amount_2024", "total", None), ("additional_tax_2024", "tax", None)]),
    ("400", [("pretax_material", "tax", None)]),
    ("405", [("pretax_investments", "tax", None)]),
]
EFFECTIVE_ONLY = {"302", "303", "312", "313", "342", "343", "400", "405"}
FLAT_ONLY = {"322", "323", "332", "333"}
REVENUE_DEDUCTIONS = ["tax_free_services", "revenue_abroad", "transfers", "non_taxable_services", "losses"]
# fields that are entered by hand on the declaration (no VAT query)
MANUAL_FIELDS = [
    ("205", "non_taxable_revenue", "Non-taxable revenue"),
    ("280", "misc", "Miscellaneous deductions"),
    ("410", "missing_pretax", "Missing pretax"),
    ("415", "pretax_correction_mixed", "Pretax correction mixed use (subtracted)"),
    ("420", "pretax_correction_other", "Pretax correction other (subtracted)"),
    ("470", "form_1050", "Form 1050"),
    ("471", "form_1055", "Form 1055"),
]

FONT = "Arial"
BOLD = Font(name=FONT, bold=True)
NORMAL = Font(name=FONT)
GREY = Font(name=FONT, color="808080")
BLUE = Font(name=FONT, color="0000FF")
RED = Font(name=FONT, color="C00000")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
TOTAL_FILL = PatternFill("solid", fgColor="F2F2F2")
WARN_FILL = PatternFill("solid", fgColor="FFF2CC")
NUM = '#,##0.00;-#,##0.00;"-"'


def attach_vat_declaration_report(doc, event=None):
    """doc_events hook (VAT Declaration, on_submit).

    Never blocks the submission: if the report cannot be built, the error is
    logged and the user is told to create it manually."""
    try:
        create_report(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "VAT declaration report failed for {0}".format(doc.name))
        frappe.msgprint(
            _("The VAT declaration was submitted, but the Excel report could not be created. Please check the Error Log."),
            indicator="orange",
            alert=True,
        )


@frappe.whitelist()
def regenerate_report(name):
    """Create the report again for an existing declaration (with TODAY's data and queries)."""
    frappe.only_for("System Manager")
    doc = frappe.get_doc("VAT Declaration", name)
    return create_report(doc)


def create_report(doc):
    generated = now_datetime()
    content = build_workbook(doc, generated)
    safe_title = (doc.title or doc.name).replace("/", "-").replace("  ", " ")
    file_name = "{0} - VAT report {1}.xlsx".format(safe_title, generated.strftime("%Y-%m-%d %H%M%S"))
    folder = create_folder(safe_title, create_folder(_("VAT Declaration"), "Home"))
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "attached_to_doctype": doc.doctype,
        "attached_to_name": doc.name,
        "folder": folder,
        "is_private": 1,
        "content": content,
    })
    file_doc.save(ignore_permissions=True)
    return file_doc.file_url


def get_relevant_codes(doc):
    codes = []
    for code, fields in CODES:
        if doc.vat_type == "flat" and code in EFFECTIVE_ONLY:
            continue
        if doc.vat_type != "flat" and code in FLAT_ONLY:
            continue
        codes.append((code, fields))
    return codes


def get_query_info(code):
    """VAT query text and version (number of saved changes, from the Version history)."""
    name = "viewVAT_{0}".format(code)
    if not frappe.db.exists("VAT query", name):
        return None
    q = frappe.db.get_value("VAT query", name, ["query", "modified", "modified_by", "creation"], as_dict=True)
    q.version = frappe.db.count("Version", {"ref_doctype": "VAT query", "docname": name})
    q.label = "v{0} (last changed {1} by {2})".format(q.version, format_datetime(q.modified, "yyyy-MM-dd HH:mm:ss"), q.modified_by)
    return q


def run_query(query, doc):
    """Same SQL as erpnextswiss kontrolle_mwst.get_data / vat_declaration.get_view_total,
    but errors are reported instead of being swallowed."""
    sql = ("""SELECT * FROM ({query}) AS `s`
              WHERE `s`.`posting_date` >= '{start_date}' AND `s`.`posting_date` <= '{end_date}'""".format(
        query=query, start_date=doc.start_date, end_date=doc.end_date).replace("{company}", doc.company))
    try:
        return frappe.db.sql(sql, as_dict=True), None
    except Exception as e:
        return [], str(e)


def build_workbook(doc, generated):
    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"
    refs, queries = {}, {}
    for code, fields in get_relevant_codes(doc):
        q = get_query_info(code)
        queries[code] = q
        if q:
            refs[code] = write_code_sheet(wb, doc, code, fields, q)
    write_summary(summary, doc, refs, queries, generated)
    write_query_sheet(wb, queries)
    wb.calculation.fullCalcOnLoad = True
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def write_code_sheet(wb, doc, code, fields, q):
    ws = wb.create_sheet(code)
    rows, error = run_query(q.query, doc)
    ws["A1"] = "Kontrolle MwSt - code {0} - {1}".format(code, doc.title)
    ws["A1"].font = Font(name=FONT, bold=True, size=12)
    ws["A2"] = "Period {0} .. {1}; query viewVAT_{2} {3}".format(doc.start_date, doc.end_date, code, q.label)
    ws["A2"].font = GREY
    first = 9
    last = first + max(len(rows), 1) - 1
    ws["A4"] = "Kontrolle MwSt total"
    ws["F4"] = "=SUM(F{0}:F{1})".format(first, last)
    ws["G4"] = "=SUM(G{0}:G{1})".format(first, last)
    ws["A5"] = "Declared value"
    ws["A6"] = "Difference (Kontrolle MwSt - declared)"
    for fieldname, measure, ratefield in fields:
        col = "F" if measure == "total" else "G"
        ws[col + "5"] = doc.get(fieldname) or 0
        ws[col + "5"].font = BLUE
        ws[col + "6"] = "={0}4-{0}5".format(col)
    ws["H5"] = ", ".join("{0} = field {1}".format("Total" if m == "total" else "Tax Amount", f) for f, m, r in fields)
    ws["H5"].font = GREY
    for c in ("A4", "A5", "A6", "F4", "G4"):
        ws[c].font = BOLD
    for c in ("F4", "G4", "F5", "G5", "F6", "G6"):
        ws[c].number_format = NUM
    if error:
        ws["A7"] = "QUERY ERROR: " + error[:500]
        ws["A7"].font = RED
    header = ["Doctype", "Document", "Date", "Taxes and Charges", "Remarks", "Total", "Tax Amount", "Check"]
    for i, h in enumerate(header, 1):
        cell = ws.cell(row=first - 1, column=i, value=h)
        cell.font = BOLD
        cell.fill = HEADER_FILL
    empty_totals = 0
    for r, row in enumerate(rows, first):
        doctype = row.get("doctype") or ""
        if doctype.startswith("tab"):
            doctype = doctype[3:]
        values = [doctype, row.get("name"), row.get("posting_date"), row.get("taxes_and_charges"),
                  str(row.get("remarks")) if row.get("remarks") is not None else None,
                  row.get("base_grand_total"), row.get("total_taxes_and_charges"), None]
        if row.get("base_grand_total") is None and any(m == "total" for f, m, rf in fields):
            values[7] = "Total is empty - missing exchange rate? Not counted."
            empty_totals += 1
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = NORMAL
            if c in (6, 7):
                cell.number_format = NUM
            if c == 3 and v:
                cell.number_format = "yyyy-mm-dd"
            if values[7]:
                cell.fill = WARN_FILL
    for col, width in zip("ABCDEFGH", (16, 20, 11, 34, 26, 16, 16, 44)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A{0}".format(first)
    return {"total": "'{0}'!F4".format(code), "tax": "'{0}'!G4".format(code), "error": error, "empty": empty_totals, "rows": len(rows)}


def write_summary(ws, doc, refs, queries, generated):
    ws["A1"] = "VAT declaration report - {0}".format(doc.title)
    ws["A1"].font = Font(name=FONT, bold=True, size=13)
    info = [
        ("Declaration", doc.name),
        ("Company", doc.company),
        ("Period", "{0} .. {1}".format(doc.start_date, doc.end_date)),
        ("VAT type", doc.vat_type),
        ("Amended from", doc.amended_from or "-"),
        ("Report generated by", frappe.session.user),
        ("Report generated", format_datetime(generated, "yyyy-MM-dd HH:mm:ss")),
    ]
    r = 2
    for k, v in info:
        ws.cell(row=r, column=1, value=k).font = BOLD
        ws.cell(row=r, column=3, value=v).font = NORMAL
        r += 1
    warnings = []
    for code, ref in refs.items():
        if ref["error"]:
            warnings.append("Query viewVAT_{0} failed: {1}".format(code, ref["error"][:200]))
        if ref["empty"]:
            warnings.append("Code {0}: {1} row(s) with an empty total (usually a missing EUR->CHF exchange rate for the month); they are NOT counted.".format(code, ref["empty"]))
    for w in warnings:
        c = ws.cell(row=r, column=1, value="WARNING: " + w)
        c.font = RED
        r += 1
    r += 1
    header = ["Code", "Field", "Measure", "Rate", "Declared", "Kontrolle MwSt (at submission)", "Difference (Kontrolle MwSt - declared)", "Query version"]
    for i, h in enumerate(header, 1):
        c = ws.cell(row=r, column=i, value=h)
        c.font = BOLD
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 32
    r += 1
    meta = frappe.get_meta("VAT Declaration")
    rowof = {}
    rated = []      # (row) of amounts with a rate -> amount x rate
    tax_rows = []   # rows that are tax amounts (382/383)
    for code, fields in get_relevant_codes(doc):
        for fieldname, measure, ratefield in fields:
            rowof[fieldname] = r
            ws.cell(row=r, column=1, value=code)
            ws.cell(row=r, column=2, value="{0} ({1})".format(_(meta.get_label(fieldname)), fieldname))
            ws.cell(row=r, column=3, value="Total" if measure == "total" else "Tax")
            if ratefield:
                ws.cell(row=r, column=4, value=(doc.get(ratefield) or 0) / 100).number_format = "0.0%"
                rated.append(r)
            elif code in ("382", "383") and measure == "tax":
                tax_rows.append(r)
            ws.cell(row=r, column=5, value=doc.get(fieldname) or 0).font = BLUE
            ref = refs.get(code)
            if ref:
                ws.cell(row=r, column=6, value="=" + ref[measure])
                ws.cell(row=r, column=7, value="=F{0}-E{0}".format(r))
                ws.cell(row=r, column=8, value=queries[code].label)
            else:
                # no query: the value can only have been entered by hand
                ws.cell(row=r, column=6, value="=E{0}".format(r))
                ws.cell(row=r, column=8, value="no VAT query viewVAT_{0} - entered by hand; copied to the Kontrolle column".format(code))
            for c in (5, 6, 7):
                ws.cell(row=r, column=c).number_format = NUM
            r += 1
    for code, fieldname, label in MANUAL_FIELDS:
        rowof[fieldname] = r
        ws.cell(row=r, column=1, value=code)
        ws.cell(row=r, column=2, value="{0} ({1})".format(label, fieldname))
        ws.cell(row=r, column=3, value="Manual")
        ws.cell(row=r, column=5, value=doc.get(fieldname) or 0).font = BLUE
        ws.cell(row=r, column=6, value="=E{0}".format(r))
        ws.cell(row=r, column=8, value="entered by hand (no query); copied to the Kontrolle column")
        for c in (5, 6):
            ws.cell(row=r, column=c).number_format = NUM
        r += 1
    r += 1

    def ref(col, fieldname):
        return "{0}{1}".format(col, rowof[fieldname]) if fieldname in rowof else "0"

    def line(label, formula_for_col, bold=False):
        nonlocal r
        ws.cell(row=r, column=2, value=label).font = BOLD
        for col in "EF":
            c = ws["{0}{1}".format(col, r)]
            c.value = formula_for_col(col)
            c.number_format = NUM
            if bold:
                c.font = BOLD
        ws["G{0}".format(r)] = "=F{0}-E{0}".format(r)
        ws["G{0}".format(r)].number_format = NUM
        for col in "BEFG":
            ws["{0}{1}".format(col, r)].fill = TOTAL_FILL
        r += 1
        return r - 1

    taxable = [f for code, fields in get_relevant_codes(doc) for f, m, rf in fields if rf]
    line("Unassigned revenue: 200 - 205 - deductions (220..280) - taxable amounts; should be 0",
         lambda col: "=" + "-".join([ref(col, "total_revenue"), ref(col, "non_taxable_revenue")]
                                    + [ref(col, f) for f in REVENUE_DEDUCTIONS + ["misc"] + taxable]))
    tax_line = line("Total tax (399) = amounts x rate + Bezugssteuer",
                    lambda col: "=" + ("+".join(["{0}{1}*$D${1}".format(col, x) for x in rated] + ["{0}{1}".format(col, x) for x in tax_rows]) or "0"))
    pretax_line = line("Total pretax (479) = 400 + 405 + 410 - 415 - 420 + 470 + 471",
                       lambda col: "={0}+{1}+{2}-{3}-{4}+{5}+{6}".format(
                           ref(col, "pretax_material"), ref(col, "pretax_investments"), ref(col, "missing_pretax"),
                           ref(col, "pretax_correction_mixed"), ref(col, "pretax_correction_other"),
                           ref(col, "form_1050"), ref(col, "form_1055")))
    line("Payable tax (500) = 399 - 479", lambda col: "={0}{1}-{0}{2}".format(col, tax_line, pretax_line), bold=True)
    ws.cell(row=r, column=2, value="Payable tax stored on the declaration").font = GREY
    c = ws.cell(row=r, column=5, value=doc.payable_tax or 0)
    c.font = BLUE
    c.number_format = NUM
    r += 2
    notes = [
        "Declared = values on the submitted VAT declaration. Kontrolle MwSt = the report 'Kontrolle MwSt' (the VAT queries the declaration reads its values from), run at the moment of submission; the per-code sheets list its rows.",
        "A difference means the value on the declaration was not (or no longer) what the query returns at submission, e.g. it was entered or changed by hand, or documents were booked after 'Get values' was pressed.",
        "The sheet 'VAT queries' holds the full text of every query used, so the numbers can be explained later even if the queries change.",
        "Blue numbers are values from the system; black numbers are formulas. All amounts in CHF.",
    ]
    for t in notes:
        ws.cell(row=r, column=1, value=t).font = GREY
        r += 1
    for col, width in zip("ABCDEFGH", (7, 52, 9, 7, 16, 18, 18, 58)):
        ws.column_dimensions[col].width = width


def write_query_sheet(wb, queries):
    ws = wb.create_sheet("VAT queries")
    for i, h in enumerate(("Code", "VAT query", "Version", "Query text"), 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = BOLD
        c.fill = HEADER_FILL
    r = 2
    for code, q in queries.items():
        ws.cell(row=r, column=1, value=code).font = NORMAL
        ws.cell(row=r, column=2, value="viewVAT_{0}".format(code)).font = NORMAL
        ws.cell(row=r, column=3, value=q.label if q else "does not exist").font = NORMAL
        c = ws.cell(row=r, column=4, value=q.query if q else None)
        c.font = Font(name="Courier New", size=9)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in (1, 2, 3):
            ws.cell(row=r, column=col).alignment = Alignment(vertical="top", wrap_text=True)
        r += 1
    for col, width in zip("ABCD", (7, 14, 30, 140)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
