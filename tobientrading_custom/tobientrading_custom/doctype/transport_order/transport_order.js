// Copyright (c) 2025, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Order', {

    setup(frm) {
        frm.set_query("link_doctype", "po_so_links", function () {
            return {
                filters: {
                    name: ['in', ['Purchase Order','Sales Order']]
                },
            };
        });
        frm.set_query("link_name", "po_so_links", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if(row.link_doctype == "Purchase Order") {
                return { filters: { docstatus: 1, per_received: ["<", "100"], status: 'To receive and bill' } };
            } else if(row.link_doctype == "Sales Order") {
                return { filters: { docstatus: 1, per_delivered: ["<", "100"], status: 'To deliver and bill' } };
            }
        });
    },
    refresh(frm) {
        if(frm.doc.docstatus == 1 && frm.doc.po_so_links.some(l => l.link_doctype == "Sales Order")) {
            frm.add_custom_button(__("Lieferschein erstellen"), () => { create_delivery_note(frm); });
        }
    },
    validate(frm) {
        check_allowed_pallet_types(frm);
        check_unique_customer_supplier(frm);
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
    customer_max_pallet_height(frm) {
        if(!frm.fetching_items) {
            for(i of frm.doc.items) {
                // Recalculate for ALL items, as we cannot know which ones were previously and which ones are now affected by the max height
                calculate_item_dimensions(frm, i.doctype, i.name);
            }
        }
    },
    customer_palletize_by_batch(frm) {
        // This parameter affects only the consolidated pallets list, not the item table
        generate_pallets_list(frm);
    },
    customer_pallet_types(frm) {
        if(!frm.fetching_items) {
            check_allowed_pallet_types(frm);
        }
    }
});


frappe.ui.form.on('Dynamic Link', {
    link_name(frm, cdt, cdn) {
        from_dt = locals[cdt][cdn].link_doctype;
        from_dn = locals[cdt][cdn].link_name;
        if(from_dt && from_dn) {
            fetch_items_from_doc(frm, from_dt, from_dn, cdn);
        }
    }
});


frappe.ui.form.on('Transport Table Item', {
    // items_add: probably nothing to do, usually item is empty when being added
    items_remove(frm, cdt, cdn) {
        generate_pallets_list(frm);
    },
    item_code(frm, cdt, cdn) {
        calculate_item_dimensions(frm, cdt, cdn);
    },
    uom(frm, cdt, cdn) {
        calculate_item_dimensions(frm, cdt, cdn);
    },
    batch(frm, cdt, cdn) {
        // Override pallet type when selecting a new Batch
        calculate_item_dimensions(frm, cdt, cdn, true);
    },
    quantity(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "amount", locals[cdt][cdn].rate * locals[cdt][cdn].quantity);
        calculate_item_dimensions(frm, cdt, cdn);
    },
    pallet_type(frm, cdt, cdn) {
        // No need to run check_allowed_pallet_types() here as that check is included in calculate_item_dimensions()
        if(locals[cdt][cdn].dimensions_calculated !== false) {
            calculate_item_dimensions(frm, cdt, cdn);
        }
    },
    rate(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "amount", locals[cdt][cdn].rate * locals[cdt][cdn].quantity);
    }
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


function fetch_items_from_doc(frm, dt, dn, dynamic_link_doc) {
    frm.fetching_items = true;
    let promises = [];
    let fetch_ref_doc = frappe.db.get_doc(dt, dn);
    promises.push(fetch_ref_doc);
    fetch_ref_doc.then(ref_doc => {
        // Set title of Dynamic Link to party of linked doc
        let party = (dt == "Sales Order" ? ref_doc.customer_name : ref_doc.supplier_name);
        frappe.model.set_value("Dynamic Link", dynamic_link_doc, "link_title", party);

        if(dt == "Sales Order") {
            update_customer_fields(frm, ref_doc);
        } else {
            update_supplier_fields(frm, ref_doc);
        }

        let added_cnt = 0;
        let ignored_cnt = 0;
        let updated_cnt = 0;
        let updated_items = [];
        for(var item of ref_doc.items) {
            // Find the current PO/SO item in the TO item list or add a new row if not present yet
            let ref_qty = item.qty - (item.received_qty || 0) - (item.delivered_qty || 0);
            let existing_items = frm.doc.items.filter(i => i.item_code == item.item_code && i.quantity == ref_qty && !updated_items.includes(i.name));
            let my_item = null;
            if(existing_items.length > 0) {
                // Item already in table: Just set a reference to Sales Order Item
                my_item = existing_items[0];
                updated_cnt++;
                // If the reference doc contains the same item several times, we want to add it several times,
                // therefore we consider each pre-existing item only once
                updated_items.push(my_item.name);
                // Update SO-Item reference if applicable
                if(dt == "Sales Order") {
                    promises.push(frappe.model.set_value(my_item.doctype, my_item.name, "sales_order_item", item.name));
                }
            } else {
                // Item not there yet: Create new row
                my_item = get_new_child_table_item(frm, item);
                if(my_item) {
                    added_cnt++;
                } else {
                    ignored_cnt++;
                    continue;
                }
            }

            // Batch assignment:
            // PO - If there is a batch matching the PO No. or referenced in the PO, overwrite the item's batch with that.
            //      Otherwise show a warning and leave the batch unchanged.
            // SO - If the item has no batch assigned yet, assign one based on FIFO principle
            if(dt == 'Purchase Order') {
                if(item.batch_no && my_item.batch != item.batch_no) {
                    promises.push(frappe.model.set_value(my_item.doctype, my_item.name, "batch", item.batch_no));
                    frappe.show_alert({message: __("Row #{0}: Batch No. updated according to {1}", [my_item.idx, ref_doc.name]), indicator: 'blue'}, 30);
                    calculate_item_dimensions(frm, my_item.doctype, my_item.name);
                } else {
                    // If no Batch is given in the reference doc, check if a matching batch by the name of the PO (-Item) exists
                    let find_matching_batch = frappe.db.get_value("Batch", {name: ['IN',[ref_doc.name,ref_doc.name+'-'+item.idx]], item: my_item.item_code}, "name");
                    promises.push(find_matching_batch);
                    find_matching_batch.then(r => {
                        if(r.message && r.message.name) {
                            promises.push(frappe.model.set_value(my_item.doctype, my_item.name, "batch", r.message.name));
                            calculate_item_dimensions(frm, my_item.doctype, my_item.name);
                            frappe.show_alert({message: __("Row #{0}: Batch not linked in PO. Matching batch '{1}' found.", [my_item.idx, r.message.name]), indicator: 'blue'}, 30);
                        }
                        else {
                            frappe.show_alert({message: __("Row #{0}: Batch not linked in PO and no matching Batch found.", [my_item.idx]), indicator: 'orange'}, 30);
                        }
                    });
                }
            }

            // Sales Order
            else if(my_item.batch) {
                // Trigger recalculation of item dimensions if batch already given
                calculate_item_dimensions(frm, my_item.doctype, my_item.name);
            } else {
                // No Batch given: Assign batches by FIFO principle, split quantity over several batches if needed
                // (Except if PO given - in that case we only want to ship batches from that PO)
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
                        let batches = r.message.batches;
                        if(batches.length == 0) {
                            frappe.show_alert({message: __("Row #{0}: No matching batches in stock", [my_item.idx]), indicator: 'red'}, 30);
                        } else {
                            if(r.message.status != 'OK') {
                                frappe.show_alert({message: __("Row #{0}: "+r.message.status, [my_item.idx]), indicator: 'orange'}, 30);
                            }
                            my_item.quantity = batches[0].qty;
                            my_item.uom = batches[0].uom; // TODO - adapt rate to new UOM here if needed
                            my_item.amount = my_item.rate * batches[0].qty;
                            promises.push(frappe.model.set_value(my_item.doctype, my_item.name, "batch", batches[0].batch_no));
                            for(var i=1; i<batches.length; i++) {
                                let extra_item = get_new_child_table_item(frm, my_item, true);
                                extra_item.quantity = batches[i].qty;
                                extra_item.uom = batches[i].uom;
                                extra_item.amount = my_item.rate * batches[i].qty;
                                extra_item.batch = batches[i].batch_no;
                                calculate_item_dimensions(frm, extra_item.doctype, extra_item.name);
                            }
                        }
                    }
                });
            }
        }

        frappe.show_alert({message: __("{0} processed. {1} Items were added, {2} updated and {3} ignored (already delivered)", [dt, added_cnt, updated_cnt, ignored_cnt]), indicator: 'blue'}, 30);

        Promise.all(promises).finally(() => {
            frm.refresh_field("items");
            frm.fetching_items = false;
        });
        // NOTE:
        // Even though we use frappe.model.set_value() to set Batch references here, Frappe doesn't fetch linked fields automatically. It would be possible to trigger this as follows:
        //   frm.refresh_field("items");
        //   frm.fields_dict.items.grid.grid_rows[0].open_row_at_index(my_item.idx);
        //   frm.fields_dict.items.grid.open_grid_row.fields_dict.batch.validate_and_set_in_model(my_item.batch);
        // However, then we don't have an event handler to know when it's completed.
        // As a simple solution, we make our get_pallet_details_for_batch() function return the required batch specs along with the rest, and set them manually.
        // Perhaps it would have been easier to implement all of the calculation logic on the server side...
    });
}


// Set supplier fields to values from a PO (as a replacement for "fetch_from" settings, as we are allowing several POs)
function update_supplier_fields(frm, po_doc) {
    if(frm.doc.supplier) {
        if(frm.doc.supplier != po_doc.supplier) {
            return false;
        }
    } else {
        frm.set_value("supplier", po_doc.supplier);
    }
    set_field_if_empty(frm, "loading_address", po_doc.loading_address);
    set_field_if_empty(frm, "contact_person", po_doc.contact_person);
    set_field_if_empty(frm, "incoterms_from_po", po_doc.incoterm);
    set_field_if_empty(frm, "incoterm_place_from_po", po_doc.incoterm_place);
    set_field_if_empty(frm, "pick_up_date", po_doc.schedule_date);
    return true;
}


// Set customer fields to values from a SO (as a replacement for "fetch_from" settings, as we are allowing several SOs)
function update_customer_fields(frm, so_doc) {
    if(frm.doc.customer) {
        if(frm.doc.customer != so_doc.customer) {
            return false;
        }
    } else {
        frm.set_value("customer", so_doc.customer);
    }
    set_field_if_empty("company_shipping_address", so_doc.shipping_address_name);
    set_field_if_empty("company_contact_person", so_doc.contact_person);
    set_field_if_empty("incoterms_from_ord", so_doc.incoterm);
    set_field_if_empty("incoterm_place_from_ord", so_doc.incoterm_place);
    set_field_if_empty("delivery_date", so_doc.delivery_date);
    set_field_if_empty("customer_max_pallet_height", so_doc.customer_max_pallet_height);
    set_field_if_empty("customer_labelling_specs", so_doc.customer_labelling_specs);

    // Process allowed pallet types
    if(so_doc.customer_pallet_types) {
        let new_pallet_types = so_doc.customer_pallet_types.map(t => t.pallet_type);
        // Pallet types already restricted: Match with restriction of this SO
        if(frm.doc.customer_pallet_types.length > 0) {
            for(pt of frm.doc.customer_pallet_types) {
                if(!new_pallet_types.includes(pt.pallet_type)) {
                    frappe.model.clear_doc(pt.doctype, pt.name);
                }
            }
            if(frm.doc.customer_pallet_types.length == 0) {
                frappe.show_alert({message: __("No allowed pallet types left after adding this Sales Order! Please check customer requirements."), indicator: 'red'}, 30);
            }
        }
        // No restriction yet: Fetch list
        else {
            new_pallet_types.forEach(pt => {
                new_cpt = frm.add_child("customer_pallet_types");
                new_cpt.pallet_type = pt;
            });
        }
        frm.refresh_field("customer_pallet_types");
    }
    if(so_doc.palletize_by_batch) {
        frm.set_value("customer_palletize_by_batch", so_doc.palletize_by_batch);
    }

    return true;
}


// Update pallet details in line items when either the item/batch/qty or customer specs are changed
function calculate_item_dimensions(frm, cdt, cdn, override_pallet_type=false) {
    let item_fields = [
        'num_full_pallets', 'full_pallet_height', 'full_pallet_net_weight', 'full_pallet_gross_weight',
        'has_rest_pallet', 'rest_pallet_height',  'rest_pallet_net_weight', 'rest_pallet_gross_weight',
        'shipment_net_weight', 'shipment_gross_weight'
    ];
    if(override_pallet_type || !locals[cdt][cdn].pallet_type) {
        // Load pallet specs from Batch unless a pallet type is specified
        item_fields = ['pallet_type', 'pallet_length', 'pallet_width', 'pallet_base_height', 'pallet_tare'].concat(item_fields);
    }
    let row = locals[cdt][cdn];
    row.dimensions_calculated = false;
    if(!row.batch) {
        row.dimensions_calculated = true;
        generate_pallets_list_when_ready(frm);
        return;
    }
    let customer_pallet_types = frm.doc.customer_pallet_types.map(t => t.pallet_type);

    if(!row.quantity) {
        return; // Quantity is mandatory, so we can fail silently here
    }
    if(row.uom != 'kg') {
        frappe.show_alert({message: __("Row #{0}: Unsupported UOM for pallet calculations: {1}", [row.idx, row.uom||'None']), indicator: 'orange'}, 30);
        return;
    }
    frappe.call({
        method: 'tobientrading_custom.tobientrading_custom.doctype.supplier_packaging_spec.supplier_packaging_spec.get_pallet_details_for_batch',
        args: {
            batch: row.batch,
            qty: row.quantity,
            customer_max_pallet_height: frm.doc.customer_max_pallet_height,
            custom_pallet_type: override_pallet_type ? '' : locals[cdt][cdn].pallet_type
        },
        callback: function(r) {
            let pallet_details = r.message;
            let model_promises =  [];
            item_fields.forEach(field => {
                model_promises.push(frappe.model.set_value(cdt, cdn, field, pallet_details[field]));
            });
            if(customer_pallet_types.length > 0 && pallet_details.pallet_type && !customer_pallet_types.includes(pallet_details.pallet_type)) {
                frappe.show_alert({message: __("Row #{0}: Pallet type '{1}' is not accepted by the customer", [row.idx, pallet_details.pallet_type]), indicator: 'red'}, 30);
            } else if(pallet_details.package_weight == 0 || !pallet_details.packaging_spec) {
                let batch_link = `<a href="/app/batch/${row.batch}">${row.batch}</a>`;
                frappe.show_alert({message: __("Row #{0}: Batch {1} has incomplete packaging details. Please update the batch, then reselect the sales order to proceed.", [row.idx, batch_link]), indicator: 'orange'}, 30);
            }
            Promise.all(model_promises).then(() => {
                row.dimensions_calculated = true;
                generate_pallets_list_when_ready(frm);
            });
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

            let rest_pallet_packing;
            if(!frm.doc.customer_palletize_by_batch) {
                // Put different items/batches together
                // TODO: For now we just do a 1D optimization of layer heights onto pallets.
                //       We could use a 3D packing library such as https://github.com/olragon/binpackingjs instead.
                rest_pallet_packing = pack_into_bins(rest_item_heights, compatible_rest_items.length, height_limit - item.pallet_base_height);
                if(!rest_pallet_packing.feasible) {
                    frappe.msgprint(__("Error: No packing found for rest pallets"));
                    continue;
                }
            } else {
                // Palletize batches individually => Use a trivial solution (one bin per item)
                rest_pallet_packing = {
                    bins: Object.keys(compatible_rest_items)
                }
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
    //frappe.show_alert({message: __("Created a pallet list with a total of {0} full pallets and {1} merged rest pallets", [total_full_pallets, total_rest_pallets]), indicator: 'blue'}, 30);
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


// Create a child table item from a SO-Item or PO-Item dataset
function get_new_child_table_item(frm, item, ignore_zero_qty = false) {
    // Deduct quantity already received/delivered (depending on source doctype)
    // => See erpnext.selling.doctype.sales_order.sales_order.make_delivery_note
    let qty = item.qty - (item.received_qty || 0) - (item.delivered_qty || 0);
    if(qty == 0 && !ignore_zero_qty) {
        return false;
    }
    let new_item = frm.add_child("items");
    new_item.item_code = item.item_code;
    new_item.required_by = item.required_by;
    new_item.item_name = item.item_name;
    new_item.quantity = qty;
    new_item.uom = item.uom;
    new_item.rate = item.rate;
    // Calculate amount to match the quantity
    new_item.amount = new_item.rate * new_item.quantity;
    new_item.batch = item.batch_no;
    if(item.doctype == "Sales Order Item") {
        new_item.sales_order_item = item.name;
    }
    return new_item;
}


function check_allowed_pallet_types(frm, idx=0) {
    let allowed_types = frm.doc.customer_pallet_types.map(t => t.pallet_type);
    let illegal_types = new Set();
    if(allowed_types.length > 0) {
        let scope = frm.doc.items;
        if(idx){
            scope = [scope[idx-1]];
        }
        for(i of scope) {
            if(!allowed_types.includes(i.pallet_type)) {
                illegal_types.add(i.pallet_type);
                // TODO: Possibly auto-repack to a suitable pallet type here in the future?
            }
        }
        if(illegal_types.size > 0) {
            let types_str = Array.from(illegal_types).join(", ");
            frappe.show_alert({message: __("The following pallet types are not accepted by the customer and must be repacked: {0}", [types_str]), indicator: 'red'}, 30);
            frappe.validated = false;
        }
    }
}


function check_unique_customer_supplier(frm) {
    let num_unique_customer_names = new Set(cur_frm.doc.po_so_links.filter(d => d.link_doctype == 'Sales Order').map(l => l.link_title)).size;
    let num_unique_supplier_names = new Set(cur_frm.doc.po_so_links.filter(d => d.link_doctype == 'Purchase Order').map(l => l.link_title)).size;
    if(num_unique_customer_names > 1 || num_unique_supplier_names > 1) {
        frappe.msgprint(__("The linked POs and SOs are from several suppliers or customers - this is not allowed."), __("Validation"));
        frappe.validated = false;
    }
}


function create_delivery_note(frm) {
    frappe.call({
        method: 'tobientrading_custom.tobientrading_custom.doctype.transport_order.transport_order.create_delivery_note',
        args: {
            transport_order: frm.doc.name
        },
        freeze: true,
        freeze_message: __("Creating Delivery Note..."),
        callback(r) {
            if(r.message) {
                frappe.show_alert({message: __("Delivery Note {0} created", [r.message]), indicator: 'green'}, 10);
                frappe.set_route("Form", "Delivery Note", r.message);
            }
        }
    });
}

function set_field_if_empty(frm, field, value) {
    let fallback = '';
    if(['Int','Float'].includes(frappe.meta.get_field(frm.doctype, field).fieldtype)) {
        fallback = 0;
    }
    if(!frm[field]) {
        frm.set_value(field, value || fallback);
    }
}