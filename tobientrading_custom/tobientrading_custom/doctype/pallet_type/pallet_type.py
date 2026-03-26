# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from tobientrading_custom.tobientrading_custom.doctype.supplier_packaging_spec.supplier_packaging_spec import get_pallet_details

class PalletType(Document):
	pass


@frappe.whitelist()
def get_pallet_details_from_type(pallet_type, pallet_max_height, package_length, package_width, package_height):
    pallet_doc = frappe.get_doc("Pallet Type", pallet_type)
    return get_pallet_details(pallet_doc.length, pallet_doc.width, pallet_doc.height, int(pallet_max_height), int(package_length), int(package_width), int(package_height))