# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
#
# Eliminate item variants.
#
# For every item template (`has_variants = 1`):
#   * 0 variants            -> simply turned into a regular item
#   * variants, <=1 in stock -> ALL variants are merged into the template, the
#                              template becomes a regular item, the variants are
#                              deleted
#   * variants, >1 in stock  -> skipped and reported (cannot safely merge several
#                              items that each still hold stock)
#
# "In stock" = SUM of `tabBin.actual_qty` > 0.
#
# History is moved by re-pointing every "Item" link from the variant(s) to the
# template DIRECTLY IN THE DATABASE. We deliberately do NOT use
# `frappe.rename_doc(..., merge=True)`: that triggers a stock valuation repost
# which is blocked by period closing
# ("Due to period closing, you cannot repost item valuation before 31.12.2024").
#
# Stock is handled explicitly (Bin + Stock Ledger Entry), because:
#   * Bin has a unique (item_code, warehouse) key, so several variants' bins
#     cannot simply be relabelled onto one template;
#   * when more than one variant transacted in the SAME warehouse, the merged
#     Stock Ledger running balance / FIFO queue has to be rebuilt so that the
#     current stock and future postings stay correct. This rebuild only touches
#     warehouses that actually received entries from more than one variant -
#     single-source warehouses keep their original, already-correct rows.
# None of this creates Stock Ledger Entries or Repost Item Valuation records, so
# the period-closing repost block is never hit.
#
# The variants are removed with `frappe.delete_doc` (NOT a raw SQL DELETE): this
# keeps Frappe's link-integrity check, so a variant that is still referenced
# somewhere we did not re-point raises an error (the whole template is rolled
# back and reported) instead of being silently orphaned.

import json

import frappe

# stock tables are handled explicitly in merge_stock(), not by the generic mover
STOCK_TABLES = {"Bin", "Stock Ledger Entry"}

# numeric "open order" columns of a Bin that are additive across merged items
BIN_AGGREGATE_FIELDS = [
    "reserved_qty",
    "ordered_qty",
    "indented_qty",
    "planned_qty",
    "reserved_qty_for_production",
    "reserved_qty_for_sub_contract",
    "reserved_qty_for_production_plan",
    "reserved_stock",
]


def execute():
    templates = frappe.get_all("Item", filters={"has_variants": 1}, pluck="name")
    if not templates:
        print("No item templates (has_variants = 1) found - nothing to do.")
        return

    link_fields = [(dt, fn) for dt, fn in get_item_link_fields() if dt not in STOCK_TABLES]

    converted = []
    converted_empty = []
    skipped_blocked = []
    failed = []

    for template in templates:
        variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

        if not variants:
            # a template without any variants: just turn it into a regular item
            try:
                convert_template_to_item(template)
                frappe.db.commit()
                converted_empty.append(template)
            except Exception as err:
                frappe.db.rollback()
                failed.append((template, [], str(err)))
                print("   ! FAILED to convert empty template '{0}': {1}".format(template, err))
            continue

        in_stock = [v for v in variants if current_stock(v) > 0]
        if len(in_stock) > 1:
            skipped_blocked.append((template, len(variants), len(in_stock)))
            print("SKIP '{0}': {1} variants, {2} currently in stock (> 1) - {3}".format(
                template, len(variants), len(in_stock), ", ".join(in_stock)))
            continue

        print("Merging {0} variant(s) into '{1}': {2}".format(
            len(variants), template, ", ".join(variants)))
        try:
            for variant in variants:
                reassign_item_links(link_fields, variant, template)
            convert_template_to_item(template)
            merge_stock(template, variants)
            for variant in variants:
                # delete_doc keeps the link-integrity check: a still-referenced
                # variant raises here instead of being orphaned
                frappe.delete_doc("Item", variant, ignore_permissions=True)
            frappe.db.commit()
            converted.append((template, list(variants)))
        except Exception as err:
            frappe.db.rollback()
            failed.append((template, list(variants), str(err)))
            print("   ! FAILED for '{0}': {1}".format(template, err))

    _print_summary(converted, converted_empty, skipped_blocked, failed)


# ----------------------------------------------------------------------------- helpers

def current_stock(item):
    qty = frappe.db.sql(
        "SELECT COALESCE(SUM(actual_qty), 0) FROM `tabBin` WHERE item_code = %s", (item,)
    )[0][0]
    return float(qty or 0)


def get_item_link_fields():
    """Every (doctype, fieldname) of a Link field that points to "Item",
    standard fields and custom fields alike."""
    single_doctypes = set(frappe.get_all("DocType", filters={"issingle": 1}, pluck="name"))

    fields = []
    standard = frappe.get_all("DocField",
        filters={"fieldtype": "Link", "options": "Item"},
        fields=["parent as doctype", "fieldname"])
    custom = frappe.get_all("Custom Field",
        filters={"fieldtype": "Link", "options": "Item"},
        fields=["dt as doctype", "fieldname"])

    for row in standard + custom:
        doctype = row.get("doctype")
        fieldname = row.get("fieldname")
        if not doctype or not fieldname:
            continue
        # the template pointer on the Item itself is handled separately and the
        # variant is deleted anyway
        if doctype == "Item" and fieldname == "variant_of":
            continue
        # single doctypes store their values in `tabSingles`, not in an own table
        if doctype in single_doctypes:
            continue
        fields.append((doctype, fieldname))

    return fields


def reassign_item_links(link_fields, variant, template):
    """Re-point every (non-stock) Item link from the variant to the template."""
    for doctype, fieldname in link_fields:
        try:
            frappe.db.sql("""
                UPDATE `tab{doctype}`
                SET `{fieldname}` = %(template)s
                WHERE `{fieldname}` = %(variant)s
            """.format(doctype=doctype, fieldname=fieldname),
                {"template": template, "variant": variant})
        except Exception as err:
            print("   ! could not move {0}.{1}: {2}".format(doctype, fieldname, err))


def convert_template_to_item(template):
    """Turn the former template into a regular item."""
    frappe.db.sql("""DELETE FROM `tabItem Variant Attribute` WHERE parent = %(t)s""", {"t": template})
    frappe.db.sql("""
        UPDATE `tabItem` SET has_variants = 0, variant_based_on = NULL WHERE name = %(t)s
    """, {"t": template})


# ----------------------------------------------------------------------------- stock

def merge_stock(template, variants):
    """Move stock ledger + bins of all variants onto the template."""
    # which warehouse received Stock Ledger Entries from more than one source?
    # (the template itself is included - it normally has none, but a stray
    #  template ledger/bin must still count as a source)
    wh_sources = {}
    for item in list(variants) + [template]:
        for (warehouse,) in frappe.db.sql(
            "SELECT DISTINCT warehouse FROM `tabStock Ledger Entry` WHERE item_code = %s", (item,)
        ):
            wh_sources.setdefault(warehouse, set()).add(item)

    # relabel the ledger onto the template
    for variant in variants:
        frappe.db.sql(
            "UPDATE `tabStock Ledger Entry` SET item_code = %s WHERE item_code = %s",
            (template, variant))

    # rebuild the merged running balance / FIFO queue, but only where it is
    # actually mixed (single-source warehouses keep their correct rows)
    for warehouse, sources in wh_sources.items():
        if len(sources) > 1:
            recompute_fifo(template, warehouse)

    rebuild_bins(template, variants)


def recompute_fifo(item_code, warehouse):
    """Replay the merged Stock Ledger of one (item, warehouse) as FIFO and write
    back qty_after_transaction / stock_value / valuation_rate / stock_queue."""
    sles = frappe.db.sql("""
        SELECT name, actual_qty, incoming_rate, valuation_rate, stock_value_difference
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
        ORDER BY posting_date, posting_time, creation
    """, (item_code, warehouse), as_dict=True)

    queue = []          # FIFO queue of [qty, rate]
    prev_value = 0.0
    for sle in sles:
        qty = float(sle.actual_qty or 0)
        if qty >= 0:
            rate = float(sle.incoming_rate or 0)
            if not rate and qty:
                rate = float(sle.stock_value_difference or 0) / qty
            if qty:
                queue.append([qty, rate])
        else:
            out = -qty
            while out > 1e-9 and queue:
                if queue[0][0] <= out + 1e-9:
                    out -= queue[0][0]
                    queue.pop(0)
                else:
                    queue[0][0] -= out
                    out = 0.0
            if out > 1e-9:
                # consuming below zero -> carry a negative layer at the last rate
                last_rate = queue[-1][1] if queue else float(sle.valuation_rate or 0)
                queue.append([-out, last_rate])

        qty_after = sum(q for q, _ in queue)
        value = sum(q * r for q, r in queue)
        rate = (value / qty_after) if abs(qty_after) > 1e-9 else 0.0
        frappe.db.sql("""
            UPDATE `tabStock Ledger Entry`
            SET qty_after_transaction = %(qty)s,
                stock_value = %(val)s,
                stock_value_difference = %(diff)s,
                valuation_rate = %(rate)s,
                stock_queue = %(queue)s
            WHERE name = %(name)s
        """, {
            "qty": qty_after, "val": value, "diff": value - prev_value,
            "rate": rate, "queue": json.dumps([[round(q, 6), round(r, 6)] for q, r in queue]),
            "name": sle.name,
        })
        prev_value = value


def rebuild_bins(template, variants):
    """Drop the existing bins (variants' and any stray template bin) and
    (re)create one bin per warehouse for the template, with the current balance
    taken from the (merged) ledger and the open-order quantities summed from the
    old bins."""
    bin_items = list(variants) + [template]
    placeholders = ", ".join(["%s"] * len(bin_items))

    # open-order quantities per warehouse, summed across the old bins
    agg_rows = frappe.db.sql("""
        SELECT warehouse, {sums}
        FROM `tabBin`
        WHERE item_code IN ({ph})
        GROUP BY warehouse
    """.format(
        sums=", ".join("SUM(`{0}`) AS `{0}`".format(f) for f in BIN_AGGREGATE_FIELDS),
        ph=placeholders,
    ), tuple(bin_items), as_dict=True)
    aggregates = {r.warehouse: r for r in agg_rows}

    sle_warehouses = {
        w[0] for w in frappe.db.sql(
            "SELECT DISTINCT warehouse FROM `tabStock Ledger Entry` WHERE item_code = %s", (template,))
    }

    stock_uom = frappe.db.get_value("Item", template, "stock_uom")

    # remove the old bins first (frees the unique item_code+warehouse key)
    frappe.db.sql(
        "DELETE FROM `tabBin` WHERE item_code IN ({ph})".format(ph=placeholders), tuple(bin_items))

    for warehouse in sorted(sle_warehouses | set(aggregates.keys())):
        balance = frappe.db.sql("""
            SELECT qty_after_transaction, valuation_rate, stock_value
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
            ORDER BY posting_date DESC, posting_time DESC, creation DESC
            LIMIT 1
        """, (template, warehouse), as_dict=True)
        actual = float(balance[0].qty_after_transaction) if balance else 0.0
        valuation_rate = float(balance[0].valuation_rate) if balance else 0.0
        stock_value = float(balance[0].stock_value) if balance else 0.0

        agg = aggregates.get(warehouse)
        values = {f: float(agg[f] or 0) if agg else 0.0 for f in BIN_AGGREGATE_FIELDS}

        projected = (actual + values["ordered_qty"] + values["indented_qty"]
                     + values["planned_qty"] - values["reserved_qty"]
                     - values["reserved_qty_for_production"]
                     - values["reserved_qty_for_sub_contract"])

        bin_doc = frappe.get_doc({
            "doctype": "Bin",
            "item_code": template,
            "warehouse": warehouse,
            "stock_uom": stock_uom,
        }).insert(ignore_permissions=True)

        frappe.db.sql("""
            UPDATE `tabBin`
            SET actual_qty = %(actual)s, valuation_rate = %(vrate)s, stock_value = %(svalue)s,
                ma_rate = %(vrate)s, fcfs_rate = %(vrate)s, projected_qty = %(projected)s,
                reserved_qty = %(reserved_qty)s, ordered_qty = %(ordered_qty)s,
                indented_qty = %(indented_qty)s, planned_qty = %(planned_qty)s,
                reserved_qty_for_production = %(reserved_qty_for_production)s,
                reserved_qty_for_sub_contract = %(reserved_qty_for_sub_contract)s,
                reserved_qty_for_production_plan = %(reserved_qty_for_production_plan)s,
                reserved_stock = %(reserved_stock)s
            WHERE name = %(name)s
        """, dict(values, actual=actual, vrate=valuation_rate, svalue=stock_value,
                  projected=projected, name=bin_doc.name))


def _print_summary(converted, converted_empty, skipped_blocked, failed):
    print("\n--- Eliminate item variants: summary ---")
    print("Converted templates (variants merged in): {0}".format(len(converted)))
    for template, variants in converted:
        print("   {0}  <=  {1}".format(template, ", ".join(variants)))
    if converted_empty:
        print("Converted templates (no variants, just made regular items): {0}".format(
            len(converted_empty)))
    if skipped_blocked:
        print("Skipped (more than one variant in stock, handle manually): {0}".format(len(skipped_blocked)))
        for template, nv, ns in skipped_blocked:
            print("   {0}  ({1} variants, {2} in stock)".format(template, nv, ns))
    if failed:
        print("Failed (rolled back, handle manually): {0}".format(len(failed)))
        for template, variants, err in failed:
            print("   {0}  <=  {1}  :: {2}".format(template, ", ".join(variants), err))
    print("Eliminate item variants done. 🚀")
