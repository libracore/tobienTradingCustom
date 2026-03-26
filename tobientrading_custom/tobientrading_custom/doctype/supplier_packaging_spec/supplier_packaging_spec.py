# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from math import floor

class SupplierPackagingSpec(Document):
    pass
    # Finally not implementing auto-renaming, instead just use a random name, include the supplier in the description and set the description as title field
    #def on_update(self):
    #    name = f"{self.supplier} - {self.description}"
    #    if self.name != name:
    #        rename_doc(doc=self, new=name)

import math
from dataclasses import dataclass

@dataclass
class Layout:
    orientation: tuple        # (package_length, package_width) used for primary block
    n_along_length: int       # number of boxes along pallet length in primary block
    n_along_width: int        # number of boxes along pallet width in primary block
    extras: list              # list of extra placements as (description, count)
    total: int


def get_pallet_details(pallet_length, pallet_width, pallet_base_height, pallet_max_height, package_length, package_width, package_height):
    packages_per_layer = get_optimal_packages_per_layer(pallet_length, pallet_width, package_length, package_width)
    layers_per_pallet = floor((pallet_max_height - pallet_base_height) / package_height) if package_height else 0
    packages_per_pallet = packages_per_layer * layers_per_pallet
    return {'packages_per_layer': packages_per_layer, 'layers_per_pallet': layers_per_pallet, 'packages_per_pallet': packages_per_pallet}


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


@frappe.whitelist()
def get_available_package_sizes(item, supplier):
    data = frappe.get_all("Supplier Packaging Spec",["`tabSupplier Packaging Item Assignment`.nominal_package_weight"], [["Supplier Packaging Spec","supplier","=", supplier], ["item","=", item]])
    weights = [f"{row.nominal_package_weight} kg" for row in data]
    return ", ".join(weights)