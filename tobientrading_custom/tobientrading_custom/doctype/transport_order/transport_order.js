// Copyright (c) 2025, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Order', {

    setup(frm) {
        frm.set_query("purchase_order", function() {
            return {
                filters: [
                    ["Purchase Order","status", "in", ["Draft", "To Receive and Bill", "To Bill"]]
                ]
            };
        });
        frm.set_query("sales_order", function() {
            return {
                filters: [
                    ["Sales Order","status", "in", ["Draft", "To Deliver and Bill", "To Bill"]]
                ]
            };
        });
    },
    loading_address(frm) {
        if(frm.doc.loading_address) {
            fetch_loading_address_details(frm);
        }
    },
    company_shipping_address(frm) {
        if(frm.doc.company_shipping_address) {
            fetch_shipping_address_details(frm);
        }
    },
    contact_person(frm){
        if(frm.doc.contact_person) {
            fetch_contact_person_details(frm);
        }
    },
    company_contact_person(frm){
        if(frm.doc.company_contact_person) {
            fetch_company_contact_person_details(frm);
        }
    },
    purchase_order(frm) {
        if(frm.doc.purchase_order) {
            fetch_items_from_doc(frm, "Purchase Order", frm.doc.purchase_order);
        }
    },
    sales_order(frm) {
        if(frm.doc.sales_order) {
            fetch_items_from_doc(frm, "Sales Order", frm.doc.sales_order);
        }
    },
    goods_button(frm) {
        goods_desc = `Total net weight: ${frm.doc.total_net_weight.toFixed(2)} kg
Total gross weight: ${frm.doc.total_gross_weight.toFixed(2)} kg`;
        for (var pal of frm.doc.pallets) {
            goods_desc += `

Number of pallets: ${(pal.num_pallets || 0)}
Pallet: ${(pal.pallet_length || 0)/100} x ${(pal.pallet_width || 0)/100} x ${(pal.pallet_height || 0)/100} m
Net weight per pallet: ${(pal.pallet_net_weight || 0)} kg
Gross weight per pallet: ${(pal.pallet_gross_weight || 0)} kg`;
        }
        frm.set_value("goods", goods_desc);
    },
});

frappe.ui.form.on('Transport Order Pallet Spec', {
    pallets_add(frm, cdt, cdn) {
        update_total_weights(frm);
    },
    pallets_remove(frm, cdt, cdn) {
        update_total_weights(frm);
    },
    num_pallets(frm, cdt, cdn) {
        update_total_weights(frm);
    },
    pallet_net_weight(frm, cdt, cdn) {
        update_total_weights(frm);
    },
    pallet_gross_weight(frm, cdt, cdn) {
        update_total_weights(frm);
    },
});

function fetch_company_contact_person_details(frm){
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Contact",
            name: frm.doc.company_contact_person
        },
        async: false,
        callback(response) {
            let contact = response.message;
            let name = ( contact.salutation || "" )  + " " + contact.first_name + " " + contact.last_name;
            let phone = ( contact.phone || contact.mobile_no );
            frm.set_value("company_contact", name || "");
            frm.set_value("company_phone", phone || "");
            frm.set_value("company_email", contact.email_id || "");
        }
    });
}


function fetch_contact_person_details(frm){
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Contact",
            name: frm.doc.contact_person
        },
        async: false,
        callback(response) {
            let contact = response.message;
            let name = ( contact.salutation || "" )  + " " + contact.first_name + " " + contact.last_name;
            let phone = ( contact.phone || contact.mobile_no );
            frm.set_value("contact", name || "");
            frm.set_value("phone", phone || "");
            frm.set_value("email", contact.email_id || "");
        }
    });
}


function fetch_loading_address_details(frm) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Address",
            name: frm.doc.loading_address
        },
        async: false,
        callback(response) {
            let address = response.message;
            let details = "<b>" + address.address_title + "</b><br>" + address.address_line1 + "<br>" + address.pincode + " " + address.city + "<br>" + address.country;
            cur_frm.set_value("loading_address_details", details);
        }
    });
}


function fetch_shipping_address_details(frm) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Address",
            name: frm.doc.company_shipping_address
        },
        async: false,
        callback(response) {
            let address = response.message;
            let details = "<b>" + address.address_title + "</b><br>" + address.address_line1 + "<br>" + address.pincode + " " + address.city + "<br>" + address.country;
            cur_frm.set_value("shipping_address_details", details);
        }
    });
}


function fetch_items_from_doc(frm, dt, dn) {
    frappe.db.get_doc(dt, dn).then(ref_doc => {
        // Sales Order: Fetch allowed pallet types as well
        if(dt == "Sales Order" && ref_doc.customer_pallet_types) {
            frm.fields_dict.customer_pallet_types.set_value([]).then(() => {
                ref_doc.customer_pallet_types.forEach(pt => {
                    new_cpt = frm.add_child("customer_pallet_types");
                    new_cpt.pallet_type = pt.pallet_type;
                });
                frm.refresh_field("customer_pallet_types");
            });
        }

        // Clear item table and add items from reference doc
        // (Only fetch items from SO if no PO selected)
        if(dt == "Purchase Order" || !frm.doc.purchase_order) {
            frm.set_value("items",[]);
            for(var item of ref_doc.items) {
                let new_item = frm.add_child("items");
                new_item.item_code = item.item_code;
                new_item.required_by = item.required_by;
                new_item.item_name = item.item_name;
                new_item.quantity = item.qty;
                new_item.uom = item.uom;
                new_item.rate = item.rate;
                new_item.amount = item.amount;
                new_item.batch = item.batch_no;
                new_item.dimensions_calculated = false;
                // If no Batch is given in the reference doc, check if a matching batch by the name of the PO exists
                if(dt == "Purchase Order" && !new_item.batch) {
                    frappe.db.get_value("Batch", {name: ref_doc.name, item: new_item.item_code}, "name").then(val => {
                        if(val.length > 0) {
                            frappe.model.set_value(new_item.doctype, new_item.name, "batch", ref_doc.name);
                            frappe.show_alert({message: __("Row #{0}: Batch not linked in PO. Matching batch '{1}' found.", [new_item.idx, ref_doc.name]), indicator: 'blue'});
                        }
                        else {
                            frappe.show_alert({message: __("Row #{0}: Batch not linked in PO and no matching Batch found. Please set Batch in PO to proceed.", [new_item.idx]), indicator: 'red'}, 30);
                        }
                        calculate_item_dimensions(frm, new_item.doctype, new_item.name);
                    });
                } else if(new_item.batch) {
                    calculate_item_dimensions(frm, new_item.doctype, new_item.name);
                } else {
                    // dt == "Sales Order", kein Batch hinterlegt => Batches nach FIFO-Prinzip zuordnen
                    frappe.call({
                        method: 'tobientrading_custom.tobientrading_custom.doctype.transport_order.transport_order.get_matching_batches',
                        args: {
                            sales_order: dn,
                            sales_order_item: item.name,
                        },
                        callback: function(r) {
                            if(!r.message || !r.message.batches){
                                return;
                            }
                            if(r.message.status != 'OK') {
                                frappe.show_alert({message: __("Row #{0}: "+r.message.status, [new_item.idx]), indicator: 'orange'}, 30);
                            }
                            let batches = r.message.batches;
                            if(batches.length == 0) {
                                frappe.show_alert({message: __("Row #{0}: No matching batches in stock", [new_item.idx]), indicator: 'red'}, 30);
                            } else {
                                new_item.batch = batches[0].batch_no;
                                new_item.quantity = batches[0].qty;
                                new_item.uom = batches[0].uom; // TODO - adapt rate to new UOM here if needed
                                new_item.amount = new_item.rate * batches[0].qty;
                                for(var i=1; i<batches.length; i++) {
                                    let extra_line_item = frm.add_child("items");
                                    extra_line_item.item_code = new_item.item_code;
                                    extra_line_item.required_by = new_item.required_by;
                                    extra_line_item.item_name = new_item.item_name;
                                    extra_line_item.quantity = batches[i].qty;
                                    extra_line_item.uom = batches[i].uom;
                                    extra_line_item.rate = new_item.rate; // TODO - adapt rate to new UOM here if needed
                                    extra_line_item.amount = new_item.rate * batches[i].qty;
                                    extra_line_item.batch = batches[i].batch_no;
                                    extra_line_item.dimensions_calculated = false;
                                }
                            }
                        }
                    );

                    frappe.show_alert({message: __("Row #{0}: Batch not linked in {1}. Please set Batch in {1} to proceed.", [new_item.idx, ref_doc.doctype]), indicator: 'red'}, 30);
                    new_item.dimensions_calculated = true;
                }
            }
        }
        frappe.show_alert({message: __("Fetched {0} Items from {1}", [ref_doc.items.length, dt]), indicator: 'blue'});
        frm.refresh_field("items");
        // NOTE:
        // The way we set Batch references here, Frappe doesn't fetch linked fields automatically. It would be possible to trigger this as follows:
        //   frm.refresh_field("items");
        //   frm.fields_dict.items.grid.grid_rows[0].open_row_at_index(new_item.idx);
        //   frm.fields_dict.items.grid.open_grid_row.fields_dict.batch.validate_and_set_in_model(new_item.batch);
        // However, then we don't have an event handler to know when it's completed.
        // As a simple solution, we make our get_pallet_details_for_batch() function return the required batch specs along with the rest, and set them manually.
        // Perhaps it would have been easier to implement all of the calculation logic on the server side...
    });
}


function calculate_item_dimensions(frm, cdt, cdn) {
    let item_fields = [
        'pallet_length', 'pallet_width', 'pallet_base_height', 'pallet_tare',
        'num_full_pallets', 'full_pallet_height', 'full_pallet_net_weight', 'full_pallet_gross_weight',
        'has_rest_pallet', 'rest_pallet_height',  'rest_pallet_net_weight', 'rest_pallet_gross_weight',
        'shipment_net_weight', 'shipment_gross_weight'
    ];
    let row = locals[cdt][cdn];
    if(!row.batch) {
        row.dimensions_calculated = true;
        generate_pallets_list_when_ready(frm);
        return;
    }
    let customer_pallet_types = frm.doc.customer_pallet_types.map(t => t.pallet_type);

    if(row.uom != 'kg') {
        frappe.show_alert({message: __("Row #{0}: Unsupported UOM for pallet calculations: {1}", [row.idx, row.uom]), indicator: 'orange'}, 30);
        return;
    }
    frappe.call({
        method: 'tobientrading_custom.tobientrading_custom.doctype.supplier_packaging_spec.supplier_packaging_spec.get_pallet_details_for_batch',
        args: {
            batch: row.batch,
            qty: row.quantity,
            customer_max_pallet_height: frm.doc.customer_max_pallet_height,
        },
        callback: function(r) {
            let pallet_details = r.message;
            item_fields.forEach(field => {
                frappe.model.set_value(cdt, cdn, field, pallet_details[field]);
            });
            if(customer_pallet_types.length > 0 && pallet_details.pallet_type && !customer_pallet_types.includes(pallet_details.pallet_type)) {
                frappe.show_alert({message: __("Row #{0}: Pallet type '{1}' is not accepted by the customer", [row.idx, pallet_details.pallet_type]), indicator: 'red'}, 30);
            } else {
                frappe.show_alert({message: __("Row #{0}: Updated pallet details", [row.idx]), indicator: 'blue'});
            }
            row.dimensions_calculated = true;
            generate_pallets_list_when_ready(frm);
        }
    });
}


// Check if calculate_item_dimensions() is done for all Items, and only then call generate_pallets_list().
// This function is called every time calculate_item_dimensions() terminates or fails for some Item
function generate_pallets_list_when_ready(frm) {
    if(frm.doc.items.every(i => i.dimensions_calculated)) {
        generate_pallets_list(frm);
    }
}


function generate_pallets_list(frm) {
    // TODO - check if mixed-batch / mixed-item pallets are allowed
    frm.set_value("pallets", []);
    let used_items = [];
    let total_full_pallets = 0;
    // For each unused Item row, find other unused rows with exactly the same full pallet specs and create a common entry in the pallets list
    for (var item of frm.doc.items) {
        if(item.num_full_pallets > 0 && !used_items.includes(item.idx)) {
            let new_pallet_type = frm.add_child("pallets");
            new_pallet_type.pallet_length = item.pallet_length;
            new_pallet_type.pallet_width = item.pallet_width;
            new_pallet_type.pallet_height = item.full_pallet_height;
            new_pallet_type.pallet_net_weight = item.full_pallet_net_weight;
            new_pallet_type.pallet_gross_weight = item.full_pallet_gross_weight;
            used_items.push(item.idx);
            let same_pallets = frm.doc.items.filter(i =>
                i.num_full_pallets > 0 &&
                !used_items.includes(i.idx) &&
                i.pallet_length == item.pallet_length &&
                i.pallet_width == item.pallet_width &&
                i.pallet_base_height == item.pallet_base_height &&
                i.pallet_tare == item.pallet_tare &&
                i.full_pallet_height == item.full_pallet_height &&
                i.full_pallet_net_weight == item.full_pallet_net_weight &&
                i.full_pallet_gross_weight == item.full_pallet_gross_weight
            );
            new_pallet_type.num_pallets = item.num_full_pallets || 0;
            let item_names = new Set([ item.item_name ]); // List of unique item names
            for (var sp of same_pallets) {
                used_items.push(sp.idx);
                new_pallet_type.num_pallets += sp.num_full_pallets;
                item_names.add(sp.item_name);
            }
            new_pallet_type.items = Array.from(item_names).join(", ")
            total_full_pallets += new_pallet_type.num_pallets;
        }
    }

    // For each unused rest pallet, find other unused rest pallets with compatible pallet specs
    // Then determine the optimal configuration for these pallets
    used_items = [];
    let total_rest_pallets = 0;
    for (var item of frm.doc.items) {
        if(item.has_rest_pallet && !used_items.includes(item.idx)) {
            used_items.push(item.idx);
            height_limit = Math.min(frm.doc.customer_max_pallet_height, item.pallet_max_height);
            let compatible_rest_items = frm.doc.items.filter(i =>
                i.has_rest_pallet &&
                !used_items.includes(i.idx) &&
                i.pallet_length == item.pallet_length &&
                i.pallet_width == item.pallet_width &&
                i.pallet_base_height == item.pallet_base_height &&
                i.pallet_tare == item.pallet_tare
            );
            for (var i of compatible_rest_items) {
                used_items.push(i.idx);
                height_limit = Math.min(height_limit, i.pallet_max_height);
            }
            compatible_rest_items.push(item);
            rest_item_heights = compatible_rest_items.map(i => i.rest_pallet_height - i.pallet_base_height);

            // Pack rest items onto pallets
            // TODO: For now we just do a 1D optimization of layer heights onto pallets.
            //       We could use a 3D packing library such as https://github.com/olragon/binpackingjs instead.
            let rest_pallet_packing = pack_into_bins(rest_item_heights, compatible_rest_items.length, height_limit - item.pallet_base_height);
            if(!rest_pallet_packing.feasible) {
                frappe.msgprint(__("Error: No packing found for rest pallets"));
                continue;
            }

            // Calculate specs of each rest pallet
            for (var pallet of rest_pallet_packing.bins) {
                if(pallet.length > 0) {
                    let net_weight = 0;
                    let gross_weight = item.pallet_tare;
                    let height = item.pallet_base_height;
                    let item_names = new Set();
                    // Sum up specs of height/weights of rest items assigned to this pallet
                    for (var item_idx of pallet) {
                        let pallet_item = compatible_rest_items[item_idx];
                        net_weight += pallet_item.rest_pallet_net_weight;
                        gross_weight += pallet_item.rest_pallet_gross_weight - pallet_item.pallet_tare;
                        item_names.add(pallet_item.item_name);
                        height += rest_item_heights[item_idx];
                    }
                    // Check if the resulting pallet is identical to a pallet type we already have
                    existing_pallet = frm.doc.pallets.find(p =>
                        p.pallet_length == item.pallet_length &&
                        p.pallet_width == item.pallet_width &&
                        p.pallet_height == height &&
                        p.net_weight == net_weight &&
                        p.gross_weight == gross_weight
                    );
                    // If so, increment the number of this type of pallet
                    if(existing_pallet) {
                        existing_pallet.num_pallets += 1;
                        // If some Items are not present in the items text, append them to it
                        // TODO/NOTE: We could store the list of Items as JSON to cover edge cases where one Item's name is contained in the other,
                        //            but let's neglect this possibility in favor of a simple, human-readable, comma-separated list
                        for (var i of item_names) {
                            if(!existing_pallet.items.includes(i)) {
                                existing_pallet.items += ", "+i;
                            }
                        }
                    // Otherwise create a new pallet type
                    } else {
                        let new_pallet = frm.add_child("pallets");
                        new_pallet.num_pallets = 1;
                        new_pallet.pallet_length = item.pallet_length;
                        new_pallet.pallet_width = item.pallet_width;
                        new_pallet.pallet_height = height;
                        new_pallet.pallet_net_weight = net_weight;
                        new_pallet.pallet_gross_weight = gross_weight;
                        new_pallet.items = Array.from(item_names).join(", ");
                    }
                    total_rest_pallets += 1;
                }
            }
        }
    }
    frappe.show_alert({message: __("Created a pallet list with a total of {0} full pallets and {1} merged rest pallets", [total_full_pallets, total_rest_pallets]), indicator: 'blue'});
    frm.refresh_field("pallets");
    update_total_weights(frm);
}


function update_total_weights(frm) {
    let total_net_weight = 0;
    let total_gross_weight = 0;
    for (var p of frm.doc.pallets) {
        total_net_weight += (p.num_pallets * p.pallet_net_weight) || 0;
        total_gross_weight += (p.num_pallets * p.pallet_gross_weight) || 0;
    }
    frm.set_value("total_net_weight", total_net_weight);
    frm.set_value("total_gross_weight", total_gross_weight);
}


// Depth-first backtracking solver for packing items (layer heights) into pallets
// Returns { feasible: boolean, assignment: Array(binIndex) | null, bins: Array(Array(itemIndices)) }
// items: array of heights
// B: number of pallets (bins)
// H: height per pallet
function pack_into_bins(items, B, H) {
  const n = items.length;
  const idx = items.map((h,i) => i).sort((a,b) => items[b] - items[a]); // indices sorted by descending height
  const sorted = idx.map(i => items[i]);

  // quick lower-bound check
  const total = items.reduce((s,x)=>s+x,0);
  if (Math.ceil(total / H) > B) return { feasible: false, assignment: null, bins: null };

  // remaining capacities and assignment (by sorted order)
  const rem = Array(B).fill(H);
  const assignSorted = Array(n).fill(-1);
  let solutionAssign = null;
  let found = false;

  // DFS
  function dfs(pos) {
    if (found) return true;
    if (pos === n) {
      // build assignment mapped back to original indices
      const assignment = Array(n).fill(-1);
      for (let s = 0; s < n; s++) assignment[idx[s]] = assignSorted[s];
      const bins = Array.from({length: B}, () => []);
      for (let i = 0; i < n; i++) {
        if (assignment[i] >= 0) bins[assignment[i]].push(i);
      }
      solutionAssign = { assignment, bins };
      found = true;
      return true;
    }

    const h = sorted[pos];

    // try bins in order, but skip equivalent remaining capacities to avoid symmetric tries
    const triedRem = new Set();
    for (let b = 0; b < B; b++) {
      if (rem[b] < h) continue;
      if (triedRem.has(rem[b])) continue; // symmetry skip
      triedRem.add(rem[b]);

      // place
      rem[b] -= h;
      assignSorted[pos] = b;

      // additional pruning: if an item exactly fits, prefer that and avoid other placements of same size
      if (dfs(pos + 1)) return true;

      // undo
      assignSorted[pos] = -1;
      rem[b] += h;

      // symmetry: if this bin was empty before placing and placing here failed, no need to try other empty bins
      if (rem[b] === H) break;
    }
    return false;
  }

  dfs(0);
  return { feasible: found, assignment: solutionAssign ? solutionAssign.assignment : null, bins: solutionAssign ? solutionAssign.bins : null };
}