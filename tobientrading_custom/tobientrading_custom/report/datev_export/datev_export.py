# Copyright (c) 2023-2026, Microsynth, libracore and contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import shutil
import hashlib
import tempfile
from datetime import datetime
import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued
import json
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
#from microsynth.microsynth.invoicing import get_microsynth_zugferd_xml as create_zugferd_xml
#from microsynth.microsynth.invoicing import create_pdf_attachment
from tobientrading_custom.tobientrading_custom.utils import attach_pdf_hook
import re
import html
import unicodedata

DATEV_CHARACTER_PATTERNS = {
    'p10040': "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$%*+-",        # dropped & to prevent xml encing issues
    'p10027': "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.",
    'p10036': "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$%*+- ",
}

EXPORT_FOLDER = 'DATEV Export'                  # File Manager folder below Home, holds the zip files
EXPORT_RETENTION_DAYS = 30                      # zip files older than this are deleted on each new export


def strip_str_to_allowed_chars(s, min_length, max_length, allowed_chars):
    out = ""
    if not s and min_length == 0:
        return out
    elif not s:
        #frappe.log_error(f"Got no value for s", "datev_export.strip_str_to_allowed_chars")
        return out
    # append each valid character
    for c in s:
        if c in allowed_chars:
            out += c
    # crop length
    out = out[:max_length]
    # verify min_length
    if len(out) < min_length:
        out += (len(out) - min_length) * allowed_chars[0]
    return out

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    columns = []
    if filters.get("version") == "AT":
        columns = [
            {"label": _("satzart"), "fieldname": "entry_type", "fieldtype": "Data", "width": 20},
#            {"label": _("External debtor number"), "fieldname": "ext_debitor_number", "fieldtype": "Data", "width": 120},
            {"label": _("gkonto"), "fieldname": "account", "fieldtype": "Data", "width": 80},
            {"label": _("belegnr"), "fieldname": "document", "fieldtype": "Dynamic Link", "options": "document_type", "width": 120},
            {"label": _("belegdatum"), "fieldname": "date", "fieldtype": "Date", "width": 80},
            {"label": _("buchsymbol"), "fieldname": "book_symbol", "fieldtype": "Data", "width": 80},
            {"label": _("buchcode"), "fieldname": "book_code", "fieldtype": "Data", "width": 80},
            {"label": _("prozent"), "fieldname": "vat_percent", "fieldtype": "Percent", "width": 80},
            {"label": _("steuercode"), "fieldname": "vat_code", "fieldtype": "Data", "width": 80},
            {"label": _("betrag"), "fieldname": "gross_amount", "fieldtype": "Float", "width": 100, "precision": 2},
            {"label": _("steuer"), "fieldname": "vat_amount", "fieldtype": "float", "width": 100, "precision": 2},
            {"label": _("text"), "fieldname": "description", "fieldtype": "Data", "width": 120},
            {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Data", "width": 120},
            {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 250}
        ]
    return columns

def get_data(filters, short=False):
    sql_query = ""
    if filters.get("version") == "AT":
        if filters.get("transactions") == "Debtors":
            sql_query = """
                SELECT
                    0 AS `entry_type`,
                    (SELECT
                        SUBSTRING(`tabSales Invoice Item`.`income_account`, 1, 4)
                     FROM `tabSales Invoice Item`
                     WHERE `tabSales Invoice Item`.`parent` = `tabSales Invoice`.`name`
                     ORDER BY `tabSales Invoice Item`.`idx` ASC
                     LIMIT 1) AS `account`,
                    "Sales Invoice" AS `document_type`,
                    `tabSales Invoice`.`name` as `document`,
                    `tabSales Invoice`.`posting_date` as `date`,
                    "AR" AS `book_symbol`,
                    "" AS `book_code`,
                    ROUND(100 * `tabSales Invoice`.`total_taxes_and_charges` / `tabSales Invoice`.`net_total`, 1) AS `vat_percent`,
                    `tabSales Invoice`.`grand_total` AS `gross_amount`,
                    (-1) * `tabSales Invoice`.`total_taxes_and_charges` AS `vat_amount`,
                    "Rechnung" AS `description`,
                    `tabSales Invoice`.`customer` AS `customer`,
                    `tabSales Invoice`.`customer_name` AS `customer_name`
                FROM `tabSales Invoice`
                LEFT JOIN `tabCustomer` ON `tabCustomer`.`name` = `tabSales Invoice`.`customer`
                WHERE
                    `tabSales Invoice`.`docstatus` = 1
                    AND `tabSales Invoice`.`company` = "{company}"
                    AND `tabSales Invoice`.`posting_date` >= "{from_date}"
                    AND `tabSales Invoice`.`posting_date` <= "{to_date}"
            """.format(
                company=filters.get("company"),
                from_date=filters.get("from_date"),
                to_date=filters.get("to_date"))

        elif filters.get("transactions") == "Creditors":
            sql_query = """
                SELECT
                    0 AS `entry_type`,
                    (SELECT
                        SUBSTRING(`tabPurchase Invoice Item`.`expense_account`, 1, 4)
                     FROM `tabPurchase Invoice Item`
                     WHERE `tabPurchase Invoice Item`.`parent` = `tabPurchase Invoice`.`name`
                     ORDER BY `tabPurchase Invoice Item`.`idx` ASC
                     LIMIT 1) AS `account`,
                    "Purchase Invoice" AS `document_type`,
                    `tabPurchase Invoice`.`name` as `document`,
                    `tabPurchase Invoice`.`posting_date` as `date`,
                    "ER" AS `book_symbol`,
                    "" AS `book_code`,
                    ROUND(100 * `tabPurchase Invoice`.`total_taxes_and_charges` / `tabPurchase Invoice`.`net_total`, 1) AS `vat_percent`,
                    `tabPurchase Invoice`.`grand_total` AS `gross_amount`,
                    (-1) * `tabPurchase Invoice`.`total_taxes_and_charges` AS `vat_amount`,
                    "Rechnung" AS `description`,
                    `tabPurchase Invoice`.`supplier` AS `customer`,
                    `tabPurchase Invoice`.`supplier_name` AS `customer_name`
                FROM `tabPurchase Invoice`
                LEFT JOIN `tabSupplier` ON `tabSupplier`.`name` = `tabPurchase Invoice`.`supplier`
                WHERE
                    `tabPurchase Invoice`.`docstatus` = 1
                    AND `tabPurchase Invoice`.`company` = "{company}"
                    AND `tabPurchase Invoice`.`posting_date` >= "{from_date}"
                    AND `tabPurchase Invoice`.`posting_date` <= "{to_date}"
            """.format(
                company=filters.get("company"),
                from_date=filters.get("from_date"),
                to_date=filters.get("to_date"))
    data = frappe.db.sql(sql_query, as_dict=True)
    return data


@frappe.whitelist()
def async_pdf_export(filters):
    enqueue_export("PDF", filters)


def pdf_export(filters, path):
    """
    Write the attached pdf of each document into path
    run
    bench execute tobientrading_custom.tobientrading_custom.report.datev_export.datev_export.pdf_export --kwargs "{'filters': {'version':'AT', 'company': 'Tobien Trading GmbH', 'from_date':'2026-02-01', 'to_date':'2026-02-02', 'transactions': 'Debtors' }, 'path': '/tmp/datev_test'}"
    """
    data = get_data(filters)

    for d in data:
        # performance improvement 2026-02-17: use attached pdf instead of creating a new one
        download_pdf(path=path,
            dt=d.get("document_type"),
            dn=d.get("document")
        )
        """
        if d.get("document_type") == "Sales Invoice":
            create_pdf(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
        elif d.get("document_type") == "Purchase Invoice":
            download_pdf(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
        """


@frappe.whitelist()
def async_xml_export(filters):
    enqueue_export("XML", filters)


def xml_export(filters, path):
    """
    Write a ZUGFeRD xml of each sales invoice into path
    run
    $ bench execute tobientrading_custom.tobientrading_custom.report.datev_export.datev_export.xml_export --kwargs "{'filters': {'version':'AT', 'company': 'Tobien Trading GmbH', 'from_date':'2023-01-01', 'to_date':'2023-04-14', 'transactions': 'Debtors' }, 'path': '/tmp/datev_test'}"
    """
    data = get_data(filters)

    for d in data:
        if d.get("document_type") == "Sales Invoice":
            xml = create_zugferd_xml(sales_invoice = d.get("document"), verify = True )

            #customer_node = "<ram:ID>{0}</ram:ID>".format(d.get("customer"))
            #debtor_node = "<ram:ID>{0}</ram:ID>".format(d.get("ext_debitor_number") if d.get("ext_debitor_number") else 99999)

            content_xml = xml #.replace(customer_node, debtor_node)
            file_path = "{0}/{1}.xml".format(path, d.get("document"))
            with open(file_path, mode='w') as file:
                file.write(content_xml)

        #elif d.get("document_type") == "Purchase Invoice":
            #xml = create_zugferd_xml(sales_invoice = d.get("document"), verify = True )         # TODO: this will not work for purchase invoices

            #supplier_node = "<ram:ID>{0}</ram:ID>".format(d.get("customer"))
            #creditor_node = "<ram:ID>{0}</ram:ID>".format(d.get("ext_debitor_number") if d.get("ext_debitor_number") else 99999)

            #content_xml = xml.replace(supplier_node, creditor_node)
            #file_path = "{0}/{1}.xml".format(path, d.get("document"))
            #with open(file_path, mode='w') as file:
            #    file.write(content_xml)


"""
XML-encoding and clean up
"""
def xml_normalize(s, length):
    translation_table = {
        #'ä': 'a',
        #'ö': 'o',
        #'ü': 'u',
        'ß': 'ss',
        'é': 'e',       # utf-8 0xC3 or 0xA9
        'è': 'e',
        'á': 'a',
        'à': 'a',
        'í': 'i',
        'ó': 'o',
        'ú': 'u',
        'ñ': 'n',
        'ç': 'c',
        'â': 'a',
        'ê': 'e',
        'ô': 'o',
        'î': 'i',
        'û': 'u',
        'é': 'e',       # utf-8 0xA9 or 0xC3
        'è': 'e',
        'œ': 'oe',
        'ø': 'o',
        'å': 'a',
        'æ': 'ae',
        '&': '+'
    }

    normalized_string = ''.join(translation_table.get(char, char) for char in s) # if ord(char) < 128 or char in translation_table)

    normalized_s = unicodedata.normalize('NFKD', normalized_string)

    return normalized_s[:length]


@frappe.whitelist()
def async_package_export(filters):
    enqueue_export("Package", filters)


def enqueue_export(export_type, filters):
    """
    Queue an export (like Frappe's "Download Files Backup"): the user is emailed a download link when the zip is ready
    """
    if type(filters) == str:
        filters = json.loads(filters)

    user = frappe.session.user
    user_email = frappe.get_cached_value("User", user, "email")
    if not user_email:
        frappe.throw(_("Your user has no email address, so the download link cannot be sent."))

    # do not queue the same export twice while it is still pending or running
    filter_hash = hashlib.sha256(json.dumps(filters, sort_keys=True, default=str).encode()).hexdigest()
    job_id = "datev_export::{0}::{1}::{2}".format(export_type, user, filter_hash)
    if is_job_enqueued(job_id):
        frappe.msgprint(_("This export is already running. You will receive an email on {0} with the download link.").format(user_email))
        return

    frappe.enqueue(
        method=export_and_notify_user,
        queue='long',
        timeout=600,
        job_id=job_id,
        deduplicate=True,
        export_type=export_type,
        filters=filters,
        user_email=user_email
    )
    frappe.msgprint(_("The export is being generated in the background. You will receive an email on {0} with the download link once it is ready.").format(user_email))


def export_and_notify_user(export_type, filters, user_email):
    """
    Background job: create the export files, zip them, store the zip as private file and email the download link
    run
    $ bench --site site1.local execute tobientrading_custom.tobientrading_custom.report.datev_export.datev_export.export_and_notify_user --kwargs "{'export_type': 'Package', 'filters': {'version':'AT', 'company': 'Tobien Trading GmbH', 'from_date':'2023-01-01', 'to_date':'2023-04-14', 'transactions': 'Debtors' }, 'user_email': 'someone@example.com'}"
    """
    delete_old_exports()

    try:
        with tempfile.TemporaryDirectory(prefix="datev_export_") as tmp_dir:
            path = os.path.join(tmp_dir, "export")
            os.mkdir(path)
            export_function = {'XML': xml_export, 'PDF': pdf_export, 'Package': package_export}[export_type]
            export_function(filters=filters, path=path)
            document_count = len(os.listdir(path))

            archive = shutil.make_archive(os.path.join(tmp_dir, "archive"), 'zip', root_dir=path)
            with open(archive, mode='rb') as file:
                content = file.read()

        file_doc = frappe.get_doc({
            'doctype': "File",
            'file_name': get_export_file_name(export_type, filters),
            'folder': get_export_folder(),
            'is_private': 1,
            'content': content
        })
        file_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "DATEV Export failed")
        frappe.sendmail(
            recipients=[user_email],
            subject=_("DATEV Export failed"),
            message=_("The DATEV {0} export ({1}, {2}, {3} - {4}) could not be created. Please contact your administrator.").format(
                export_type, filters.get("company"), _(filters.get("transactions")), filters.get("from_date"), filters.get("to_date")),
            now=True
        )
        raise

    file_url = frappe.utils.get_url(file_doc.file_url)
    frappe.sendmail(
        recipients=[user_email],
        subject=_("DATEV Export is ready"),
        message=_(
            "The DATEV {0} export ({1}, {2}, {3} - {4}) with {5} files is ready.<br><br>"
            "Click here to download (login required):<br>"
            "<a href='{6}'>{6}</a><br><br>"
            "The file will be deleted after {7} days."
        ).format(export_type, filters.get("company"), _(filters.get("transactions")), filters.get("from_date"),
            filters.get("to_date"), document_count, file_url, EXPORT_RETENTION_DAYS),
        now=True
    )


def get_export_file_name(export_type, filters):
    parts = ["DATEV", export_type, filters.get("company"), filters.get("transactions"),
        filters.get("from_date"), filters.get("to_date")]
    return "{0}.zip".format(re.sub(r"[^A-Za-z0-9-]+", "_", "_".join(str(p or "") for p in parts)))


def get_export_folder():
    folder = "Home/{0}".format(EXPORT_FOLDER)
    if not frappe.db.exists("File", {'name': folder, 'is_folder': 1}):
        frappe.get_doc({
            'doctype': "File",
            'file_name': EXPORT_FOLDER,
            'is_folder': 1,
            'folder': "Home",
            'is_private': 1
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
    return folder


def delete_old_exports():
    """
    Delete export zip files older than EXPORT_RETENTION_DAYS (Frappe's file backups are only pruned by count, see backups.delete_downloadable_backups)
    """
    cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -EXPORT_RETENTION_DAYS)
    old_files = frappe.get_all("File",
        filters={
            'folder': "Home/{0}".format(EXPORT_FOLDER),
            'is_folder': 0,
            'creation': ["<", cutoff]
        },
        pluck='name'
    )
    for file_name in old_files:
        try:
            frappe.delete_doc("File", file_name, ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "DATEV Export: failed to delete old export {0}".format(file_name))
    frappe.db.commit()


def create_pdf(path, dt, dn, print_format=None):
    # use the default print format of the doctype (as the print view does) unless one is given
    content_pdf = frappe.get_print(
        dt,
        dn,
        print_format=print_format or frappe.get_meta(dt).default_print_format or "Standard",
        as_pdf=True)
    file_name = "{0}.pdf".format(dn)
    content_file_name = "{0}/{1}".format(path, file_name)
    with open(content_file_name, mode='wb') as file:
        file.write(content_pdf)
    return file_name


def _get_prioritized_attachment(attachments, dt, dn):
    document_name = (dn or "").lower()
    pdf_attachments = []

    for attachment in attachments:
        file_name = (attachment.get("file_name") or "").lower()
        file_url = (attachment.get("file_url") or "").lower()
        if not file_name and file_url:
            file_name = os.path.basename(file_url).lower()

        if not file_name:
            continue

        if not file_name.endswith(".pdf"):
            continue

        # Prefer actual invoice file names and reject unrelated attachments like PO PDFs.
        if document_name in file_name:
            pdf_attachments.append(attachment)
        elif file_name.startswith("si-") and dt == "Sales Invoice":
            pdf_attachments.append(attachment)
        elif file_name.startswith("pi-") and dt == "Purchase Invoice":
            pdf_attachments.append(attachment)

    if pdf_attachments:
        return pdf_attachments[0]

    return attachments[0] if attachments else None


def download_pdf(path, dt, dn, allow_attachment_repair=True):
    file_name = "{0}.pdf".format(dn)
    content_file_name = "{0}/{1}".format(path, file_name)
    # find attachment and copy to output
    attachments = frappe.get_all(
        "File",
        filters={'attached_to_doctype': dt, 'attached_to_name': dn},
        fields=['name', 'file_url', 'file_name'],
        order_by='creation DESC'
    )
    if attachments and len(attachments) > 0:
        source_attachment = _get_prioritized_attachment(attachments, dt, dn)
        source_path = source_attachment.get('file_url') if source_attachment else None

        if source_path is None:
            source_path = attachments[0].get('file_url')

        source_file = os.path.join(frappe.utils.get_bench_path(), "sites", frappe.utils.get_site_path()[2:], source_path[1:])
        if "\"" in source_file:
            frappe.log_error(f"This file name is less than suboptimal: {dt} {dn}: {source_file}", "datev_export.download_pdf file issue")
        os.system("""cp "{0}" "{1}" """.format(source_file, content_file_name))
    else:
        # no attachment found - in case of a sales invoice, this can be created and then iterated (if allowed - prevent loop)
        if dt == "Sales Invoice" and allow_attachment_repair:
            # create the attachment
            #create_pdf_attachment(sales_invoice=dn)
            doc = frappe.get_doc(dt, dn)
            attach_pdf_hook(doc)
            # iterate this function and prevent loop
            download_pdf(path, dt, dn, allow_attachment_repair=False)
    return file_name


def create_datev_xml(path, dt, dn):
    # pre-process document to prevent datev errors
    doc = frappe.get_doc(dt, dn).as_dict()
    for item in doc['items']:
        item['item_name'] = strip_str_to_allowed_chars(item['item_name'], 1, 39, DATEV_CHARACTER_PATTERNS['p10036'])
    doc['party_name'] = strip_str_to_allowed_chars(doc.get('customer_name') or doc.get('supplier_name'), 1, 50, DATEV_CHARACTER_PATTERNS['p10036'])
    if doc['doctype'] == "Sales Invoice":
        customer_address = frappe.get_doc("Address", doc.get("customer_address"))
        doc['party_number'] = doc.get('customer')
        #doc['party_number'] = frappe.get_value("Customer", doc.customer, "ext_debitor_number")
        doc['address_line1'] = strip_str_to_allowed_chars(customer_address.address_line1, 1, 50, DATEV_CHARACTER_PATTERNS['p10036'])
        doc['pincode'] = customer_address.pincode
        doc['city'] = strip_str_to_allowed_chars(customer_address.city, 1, 11, DATEV_CHARACTER_PATTERNS['p10036'])
    else:
        supplier_address = frappe.get_doc("Address", doc.get("supplier_address"))
        doc['party_number'] = doc.get('supplier')
        #doc['party_number'] = frappe.get_value("Supplier", doc.supplier, "ext_creditor_id")
        doc['address_line1'] = strip_str_to_allowed_chars(supplier_address.address_line1, 1, 50, DATEV_CHARACTER_PATTERNS['p10036'])
        doc['pincode'] = supplier_address.pincode
        doc['city'] = strip_str_to_allowed_chars(supplier_address.city, 1, 11, DATEV_CHARACTER_PATTERNS['p10036'])
    doc['tax_id'] = strip_str_to_allowed_chars(doc.get("tax_id"), 1, 15, DATEV_CHARACTER_PATTERNS['p10027'])
    doc['bill_no'] = strip_str_to_allowed_chars(doc.get("bill_no") or doc.get('name'), 1, 36, DATEV_CHARACTER_PATTERNS['p10040'])

    datev_xml = frappe.render_template("tobientrading_custom/tobientrading_custom/report/datev_export/invoice.html", {
        'doc': doc
    })
    file_name = "{0}.xml".format(dn)
    content_file_name = "{0}/{1}".format(path, file_name)
    with open(content_file_name, mode='w') as file:
        file.write(datev_xml)
    return file_name


def create_datev_summary_xml(path, document):
    datev_summary_xml = frappe.render_template("tobientrading_custom/tobientrading_custom/report/datev_export/document.html", document)
    file_name = "document.xml"
    content_file_name = "{0}/{1}".format(path, file_name)
    with open(content_file_name, mode='w') as file:
        file.write(datev_summary_xml)
    return file_name


def package_export(filters, path):
    """
    Export the complete sales invoice package with pdf, xml and document overview into path
    run
    $ bench execute tobientrading_custom.tobientrading_custom.report.datev_export.datev_export.package_export --kwargs "{'filters': {'version':'AT', 'company': 'Tobien Trading GmbH', 'from_date':'2023-01-01', 'to_date':'2023-04-14', 'transactions': 'Debtors' }, 'path': '/tmp/datev_test'}"
    """
    data = get_data(filters)

    date = datetime.now()

    document = {
        'date': date,
        'title': 'DATEV Export',
        'documents': []
    }
    for d in data:
        if d.get("document_type") == "Sales Invoice" and d.get("gross_amount") != 0:
            # create pdf
            pdf_file = create_pdf(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
            xml_file = create_datev_xml(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
            document['documents'].append({
                'xml_filename': xml_file,
                'pdf_filename': pdf_file,
                'document_type': d.get("document_type")
            })
        elif d.get("document_type") == "Purchase Invoice" and d.get("gross_amount") != 0:
            # create pdf
            pdf_file = download_pdf(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
            xml_file = create_datev_xml(path=path,
                dt=d.get("document_type"),
                dn=d.get("document")
            )
            document['documents'].append({
                'xml_filename': xml_file,
                'pdf_filename': pdf_file,
                'document_type': d.get("document_type")
            })
    create_datev_summary_xml(path, document)


def escape_and_safe_truncate(input_string, max_length=50):
    # Escape the HTML string
    escaped_string = html.escape(input_string)

    # Early return if the string is already short enough
    if len(escaped_string) <= max_length:
        return escaped_string

    # Use a regex to extract valid parts of the string without breaking entities
    result = []
    current_length = 0
    # Regex to match entities or single characters
    entity_or_char_pattern = re.compile(r'&[a-zA-Z0-9#]+;|.')
    # Iterate through matches while keeping track of length
    for match in entity_or_char_pattern.finditer(escaped_string):
        part = match.group(0)
        part_length = len(part)
        if current_length + part_length > max_length:
            break # Stop before exceeding the max length

        result.append(part)
        current_length += part_length

    # Join the result to form the safely truncated string
    return ''.join(result)
