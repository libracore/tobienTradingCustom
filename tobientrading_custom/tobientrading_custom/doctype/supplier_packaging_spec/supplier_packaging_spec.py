# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from math import floor, ceil

class SupplierPackagingSpec(Document):
    def on_update(self):
        ensure_item_suppliers(self)

    # Finally not implementing auto-renaming, instead just use a random name, include the supplier in the description and set the description as title field
    #def on_update(self):
    #    name = f"{self.supplier} - {self.description}"
    #    if self.name != name:
    #        rename_doc(doc=self, new=name)


def ensure_item_suppliers(spec):
    """For every item assigned in the packaging spec, make sure an "Item Supplier" entry
    exists on the Item for the spec's supplier. Missing entries are created with a blank
    supplier part number."""
    if not spec.supplier:
        return
    for row in spec.items:
        if not row.item:
            continue
        if frappe.db.exists("Item Supplier", {
            "parenttype": "Item",
            "parent": row.item,
            "supplier": spec.supplier,
        }):
            continue
        item_doc = frappe.get_doc("Item", row.item)
        item_doc.append("supplier_items", {
            "supplier": spec.supplier,
            "full_supplier_name": spec.supplier_name,
            "supplier_part_no": "",
        })
        item_doc.save(ignore_permissions=True)

import math
from dataclasses import dataclass

@dataclass
class Layout:
    orientation: tuple        # (package_length, package_width) used for primary block
    n_along_length: int       # number of boxes along pallet length in primary block
    n_along_width: int        # number of boxes along pallet width in primary block
    extras: list              # list of extra placements as (description, count)
    total: int


def get_pallet_details(pallet_length, pallet_width, pallet_base_height, pallet_max_height, package_length, package_width, package_height, override_packages_per_layer=0, override_layers_per_pallet=0):
    optimal_packages_per_layer = get_optimal_packages_per_layer(pallet_length, pallet_width, package_length, package_width)
    packages_per_layer = override_packages_per_layer or optimal_packages_per_layer
    optimal_layers_per_pallet = floor((pallet_max_height - pallet_base_height) / package_height) if package_height else 0
    if optimal_layers_per_pallet and override_layers_per_pallet:
        layers_per_pallet = min(optimal_layers_per_pallet, override_layers_per_pallet)
    else:
        layers_per_pallet = override_layers_per_pallet or optimal_layers_per_pallet
    packages_per_pallet = packages_per_layer * layers_per_pallet
    return {'packages_per_layer': packages_per_layer, 'layers_per_pallet': layers_per_pallet, 'packages_per_pallet': packages_per_pallet}


@frappe.whitelist()
def get_pallet_details_for_batch(batch, qty, customer_max_pallet_height=0, custom_pallet_type=None):
    batch_doc = frappe.get_doc("Batch", batch)
    customer_max_pallet_height = int(customer_max_pallet_height or 0)
    if customer_max_pallet_height == 0:
        customer_max_pallet_height = batch_doc.pallet_max_height
    max_pallet_height = min(batch_doc.pallet_max_height, customer_max_pallet_height)
    if custom_pallet_type and custom_pallet_type != batch_doc.pallet_type:
        pt_doc = frappe.get_doc("Pallet Type", custom_pallet_type)
        details = frappe._dict(get_pallet_details(
            pt_doc.length,
            pt_doc.width,
            pt_doc.height,
            max_pallet_height,
            batch_doc.package_length,
            batch_doc.package_width,
            batch_doc.package_height
        ))
        # Return basic pallet specs along with the calculations as these aren't fetched automatically from Batch
        details.pallet_type = custom_pallet_type
        details.pallet_length = pt_doc.length
        details.pallet_width = pt_doc.width
        details.pallet_base_height = pt_doc.height
        details.pallet_tare = pt_doc.tare
    else:
        details = frappe._dict(get_pallet_details(
            batch_doc.pallet_length,
            batch_doc.pallet_width,
            batch_doc.pallet_base_height,
            max_pallet_height,
            batch_doc.package_length,
            batch_doc.package_width,
            batch_doc.package_height,
            batch_doc.packages_per_layer, # override auto-calculation
            batch_doc.layers_per_pallet,  # override auto-calculation (except if limited by max_pallet_height)
        ))
        # Return basic pallet specs along with the calculations as these aren't fetched automatically from Batch
        details.pallet_type = batch_doc.pallet_type
        details.pallet_length = batch_doc.pallet_length
        details.pallet_width = batch_doc.pallet_width
        details.pallet_base_height = batch_doc.pallet_base_height
        details.pallet_tare = batch_doc.pallet_tare
    details.package_weight = batch_doc.package_weight
    details.packaging_spec = batch_doc.packaging_spec
    # Calculate extra details from Batch specs and quantity
    details.num_packages = ceil(float(qty) / batch_doc.package_weight) if batch_doc.package_weight > 0 else 0
    details.num_full_pallets = floor(details.num_packages / details.packages_per_pallet) if details.packages_per_pallet > 0 else 0
    details.full_pallet_height = batch_doc.pallet_base_height + details.layers_per_pallet * batch_doc.package_height
    details.full_pallet_net_weight = details.packages_per_pallet * batch_doc.package_weight
    details.full_pallet_gross_weight = details.full_pallet_net_weight + batch_doc.pallet_tare + details.packages_per_pallet * batch_doc.package_tare

    if details.num_packages > details.num_full_pallets * details.packages_per_pallet:
        details.has_rest_pallet = 1
        details.rest_pallet_packages = details.num_packages - details.num_full_pallets * details.packages_per_pallet
        details.rest_pallet_layers = ceil(details.rest_pallet_packages / details.packages_per_layer) if details.packages_per_layer > 0 else 0
        details.rest_pallet_height = batch_doc.pallet_base_height + details.rest_pallet_layers * batch_doc.package_height
        details.rest_pallet_net_weight = float(qty) - details.num_full_pallets * details.full_pallet_net_weight
        details.rest_pallet_gross_weight = details.rest_pallet_net_weight + batch_doc.pallet_tare + details.rest_pallet_packages * batch_doc.package_tare
    else:
        details.has_rest_pallet = 0
        details.rest_pallet_packages = 0
        details.rest_pallet_layers = 0
        details.rest_pallet_height = 0
        details.rest_pallet_net_weight = 0
        details.rest_pallet_gross_weight = 0

    details.shipment_net_weight = details.num_full_pallets * details.full_pallet_net_weight + details.has_rest_pallet * details.rest_pallet_net_weight
    details.shipment_gross_weight = details.num_full_pallets * details.full_pallet_gross_weight + details.has_rest_pallet * details.rest_pallet_gross_weight

    return details


def get_optimal_packages_per_layer(pallet_length, pallet_width, package_length, package_width):
    """
    Compute best axis-aligned packing on a rectangular pallet given a box that may be placed
    in two horizontal orientations: (package_length x package_width) or (package_width x package_length).
    Determines a Layout describing the best packing found (including simple mixed partitioning).
    Returns the total number of cartons in this layout.
    (AI-generated and tested)
    """
    if package_length == 0 or package_width == 0 or pallet_length == 0 or pallet_width == 0:
        return 0

    def base_grid(pl, pw, bl, bw):
        nL = int(pl // bl)
        nW = int(pw // bw)
        return nL, nW, nL * nW

    best = None
    # Try both primary orientations
    orientations = [(package_length, package_width), (package_width, package_length)]
    for (bl, bw) in orientations:
        nL, nW, base = base_grid(pallet_length, pallet_width, bl, bw)

        extras_best_count = 0
        extras_best_desc = []

        # Fill leftover strips with the alternate orientation
        alt_bl, alt_bw = (bw, bl)
        leftover_length = pallet_length - nL * bl
        leftover_width = pallet_width - nW * bw

        extra1 = int(leftover_length // alt_bl) * int(pallet_width // alt_bw)
        extra2 = int(pallet_length // alt_bl) * int(leftover_width // alt_bw)

        if extra1 >= extra2:
            extras_best_count = extra1
            if extra1 > 0:
                extras_best_desc = [("leftover_length_strip_alt_orientation", extra1)]
        else:
            extras_best_count = extra2
            if extra2 > 0:
                extras_best_desc = [("leftover_width_strip_alt_orientation", extra2)]

        # Partition along pallet length
        partition_best_count = 0
        partition_best_desc = []
        max_k = int(pallet_length // bl)
        for k in range(0, max_k + 1):
            used_length = k * bl
            remaining_length = pallet_length - used_length
            countA = k * int(pallet_width // bw)
            countB = int(remaining_length // alt_bl) * int(pallet_width // alt_bw)
            if countA + countB > partition_best_count:
                partition_best_count = countA + countB
                partition_best_desc = [("k_primary_columns", k), ("primary_count", countA), ("alternate_count", countB)]

        # Partition along pallet width
        partition_w_best_count = 0
        partition_w_best_desc = []
        max_k_w = int(pallet_width // bw)
        for k in range(0, max_k_w + 1):
            used_width = k * bw
            remaining_width = pallet_width - used_width
            countA = k * int(pallet_length // bl)
            countB = int(pallet_length // alt_bl) * int(remaining_width // alt_bw)
            if countA + countB > partition_w_best_count:
                partition_w_best_count = countA + countB
                partition_w_best_desc = [("k_primary_rows", k), ("primary_count", countA), ("alternate_count", countB)]

        candidates = []
        candidates.append(("base", base, []))
        candidates.append(("base_plus_strip", base + extras_best_count, extras_best_desc))
        candidates.append(("partition_length", partition_best_count, partition_best_desc))
        candidates.append(("partition_width", partition_w_best_count, partition_w_best_desc))

        best_candidate = max(candidates, key=lambda x: x[1])

        orientation_layout = Layout(
            orientation=(bl, bw),
            n_along_length=nL,
            n_along_width=nW,
            extras=best_candidate[2],
            total=best_candidate[1]
        )

        if best is None or orientation_layout.total > best.total:
            best = orientation_layout
    if best is None:
        return 0
    return best.total


def get_available_package_sizes(item, supplier):
    data = frappe.get_all("Supplier Packaging Spec",["`tabSupplier Packaging Item Assignment`.nominal_package_weight"], [["Supplier Packaging Spec","supplier","=", supplier], ["item","=", item]])
    weights = [f"{row.nominal_package_weight} kg" for row in data]
    return ", ".join(weights)


def set_supplier_package_sizes(doc, method=None):
    """Item onload hook: fill the display-only `package_sizes` on each Item Supplier
    row server-side, so the value is part of the loaded document and does not dirty
    the form. Not persisted unless the document is explicitly saved."""
    for row in doc.get("supplier_items") or []:
        if row.supplier:
            row.package_sizes = get_available_package_sizes(doc.item_code, row.supplier)