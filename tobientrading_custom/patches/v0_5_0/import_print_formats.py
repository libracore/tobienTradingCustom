# Copyright (c) 2026, libracore AG and contributors

import json
import os

import frappe

# Print Formats shipped with this release. The JSON files next to this patch are
# manual exports of customer-tuned Print Formats. We import them via a one-off
# patch (rather than fixtures / standard format files) so that migrate does NOT
# re-import and clobber the customer's own edits on every run -- this patch runs
# exactly once, then ownership of the formats stays with the site.
PRINT_FORMAT_DIR = os.path.join(os.path.dirname(__file__), "print_formats")


def execute():
    for filename in sorted(os.listdir(PRINT_FORMAT_DIR)):
        if not filename.endswith(".json"):
            continue

        with open(os.path.join(PRINT_FORMAT_DIR, filename), encoding="utf-8") as f:
            data = json.load(f)

        name = data["name"]

        if frappe.db.exists("Print Format", name):
            doc = frappe.get_doc("Print Format", name)
            doc.update(data)
            action = "Updated"
        else:
            doc = frappe.get_doc(data)
            action = "Created"

        doc.flags.ignore_permissions = True
        doc.save()
        print(f"{action} Print Format: {name}")

    frappe.db.commit()
