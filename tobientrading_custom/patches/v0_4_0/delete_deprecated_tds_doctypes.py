# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Delete the deprecated TDS child-table DocTypes that were migrated into this
# app's own "Technical Data Sheet ..." child tables by
# tobientrading_custom.patches.v0_2_0.migrate_tds_childtables.
#
# Their data has already been copied to the new tables, so here we remove the
# old DocType definitions and drop their underlying DB tables.

import frappe

# the SOURCE (deprecated) doctypes from v0_2_0.migrate_tds_childtables.table_map
DEPRECATED_DOCTYPES = [
    "TDS Certificate Table",
    "MSDS Table",
    "Customs Tariff Table",
    "Sensoric Parameter Table",
    "Physical and Chemical Parameter Table",
    "Nutritional Information Table",
    "Microbiologiacal Propertie Table",
    "Allergene Table",
    "Packaging and Storage Table",
    "Packaging and Storage Table II",
    "Dietary Information Table",
    "Heavy Metal Table",
    "Foreign Body Table",
    "Additional Information Table",
    # Some other stale doctypes (not necessarily TDS related):
    "Country MultiSelect",
    "Attachment Table",
    "DE MwSt",
    "General Information"
]


def execute():
    for doctype in DEPRECATED_DOCTYPES:
        # delete the DocType definition (incl. its DocFields) if it still exists.
        # force=True bypasses the "standard doctype" guard; ignore_missing keeps
        # the patch idempotent on re-runs / fresh sites.
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc(
                "DocType", doctype,
                force=True, ignore_missing=True, ignore_permissions=True,
            )
            print("Deleted DocType '{0}'.".format(doctype))
        else:
            print("DocType '{0}' not found - skipping.".format(doctype))

        # drop the underlying table regardless (IF EXISTS -> safe if delete_doc
        # already removed it, or if only an orphaned table was left behind)
        frappe.db.sql_ddl("DROP TABLE IF EXISTS `tab{0}`".format(doctype))
        print("Dropped table 'tab{0}' (if it existed).".format(doctype))

    frappe.db.commit()
    print("Deleting deprecated TDS doctypes done. 🚀")
