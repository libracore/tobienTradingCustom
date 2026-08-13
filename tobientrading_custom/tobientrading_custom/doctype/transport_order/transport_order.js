// Copyright (c) 2025, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Order', {

    setup(frm) {
        if(frm.doc.docstatus == 0)  {
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
        }
    },
    refresh(frm) {
        // Drop the cached Batch packaging specs, they may have been edited in the meantime
        frm.batch_specs = {};
        if(frm.doc.docstatus == 1 && frm.doc.po_so_links && frm.doc.po_so_links.some(l => l.link_doctype == "Sales Order")) {
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
            // SO - If the item has no batch assigned yet, assign one (or several) based on FIFO principle
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
                let batches_returned = new Promise((resolve,reject) => {
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
                                if(r.message.status == 'insufficient_stock') {
                                    let missing_qty = ref_qty;
                                    batches.map(b => missing_qty -= b.qty);
                                    frappe.show_alert({message: __("Row #{0}: The available stock does not cover the full order quantity ({1} {2} missing)", [my_item.idx, missing_qty, my_item.uom]), indicator: 'orange'}, 30);
                                    // Add an item row with the remaining qty but without Batch
                                    let extra_item = get_new_child_table_item(frm, my_item, true);
                                    extra_item.quantity = missing_qty;
                                    extra_item.uom = my_item.uom;
                                    extra_item.amount = my_item.rate * missing_qty;
                                    extra_item.batch = '';
                                    calculate_item_dimensions(frm, extra_item.doctype, extra_item.name);
                                }
                                resolve();
                            }
                        }
                    });
                });
                promises.push(batches_returned);
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
    set_field_if_empty(frm, "company_shipping_address", so_doc.shipping_address_name);
    set_field_if_empty(frm, "company_contact_person", so_doc.contact_person);
    set_field_if_empty(frm, "incoterms_from_ord", so_doc.incoterm);
    set_field_if_empty(frm, "incoterm_place_from_ord", so_doc.incoterm_place);
    set_field_if_empty(frm, "delivery_date", so_doc.delivery_date);
    set_field_if_empty(frm, "customer_max_pallet_height", so_doc.customer_max_pallet_height);
    set_field_if_empty(frm, "customer_labelling_specs", so_doc.customer_labelling_specs);

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
    if(frm.doc.items.every(i => i.dimensions_calculated !== false)) {
        generate_pallets_list(frm);
    }
}


function generate_pallets_list(frm) {
    // The batch specs may have to be fetched from the server first, so this runs asynchronously
    return fetch_batch_specs(frm).then(batch_specs => build_pallets_list(frm, batch_specs));
}


// Fetch (and cache on the form) the packaging specs of every Batch used in the items table.
// Consolidating the rest pallets needs the package dimensions - only packages of identical
// specs may be stacked into common layers - as well as each batch's max pallet height.
function fetch_batch_specs(frm) {
    frm.batch_specs = frm.batch_specs || {};
    let missing = Array.from(new Set(frm.doc.items.filter(i => i.batch && !frm.batch_specs[i.batch]).map(i => i.batch)));
    if(missing.length == 0) {
        return Promise.resolve(frm.batch_specs);
    }
    return new Promise(resolve => {
        frappe.call({
            method: 'tobientrading_custom.tobientrading_custom.doctype.supplier_packaging_spec.supplier_packaging_spec.get_batch_packaging_specs',
            args: {
                batches: missing
            },
            callback(r) {
                Object.assign(frm.batch_specs, r.message || {});
                resolve(frm.batch_specs);
            }
        });
    });
}


function build_pallets_list(frm, batch_specs) {
    frm.set_value("pallets", []);

    // Full pallets: one entry per distinct pallet specification
    for (var item of frm.doc.items) {
        if(item.num_full_pallets > 0) {
            add_pallets(frm, {
                pallet_length: item.pallet_length,
                pallet_width: item.pallet_width,
                pallet_height: item.full_pallet_height,
                pallet_net_weight: item.full_pallet_net_weight,
                pallet_gross_weight: item.full_pallet_gross_weight,
                item_names: [ item.item_name ]
            }, item.num_full_pallets);
        }
    }

    // Rest pallets: group the items by pallet specs, as only pallets of the same type can be combined
    let used_items = [];
    for (var item of frm.doc.items) {
        if(!item.has_rest_pallet || used_items.includes(item.idx)) {
            continue;
        }
        let compatible_rest_items = frm.doc.items.filter(i =>
            i.has_rest_pallet &&
            !used_items.includes(i.idx) &&
            i.pallet_length == item.pallet_length &&
            i.pallet_width == item.pallet_width &&
            i.pallet_base_height == item.pallet_base_height &&
            i.pallet_tare == item.pallet_tare
        );
        compatible_rest_items.forEach(i => used_items.push(i.idx));
        add_rest_pallets(frm, compatible_rest_items, batch_specs);
    }

    frm.refresh_field("pallets");
    update_total_weights(frm);
}


// Consolidate the rest pallets of a group of items sharing the same pallet specs:
// re-stack the packages that may share a layer, then pack whatever is left onto as few pallets as possible
function add_rest_pallets(frm, rest_items, batch_specs) {
    let pallet = rest_items[0]; // Pallet specs are identical for the whole group
    let height_limit = get_max_pallet_height(frm, rest_items, batch_specs);
    if(!height_limit) {
        frappe.show_alert({message: __("No maximum pallet height is defined - rest pallets are not stacked together."), indicator: 'orange'}, 30);
    }
    // Height available for the goods, i.e. without the pallet itself
    let goods_height_limit = height_limit ? height_limit - pallet.pallet_base_height : 0;
    if(height_limit && goods_height_limit <= 0) {
        frappe.msgprint(__("The base pallet height of item '{0}' is higher than the maximum pallet height of {1} cm.", [pallet.item_name, height_limit]));
        return;
    }

    // Merge the packages that may be stacked into common layers, then fill up whole pallets with them.
    // What remains of every merged entry is a block of layers to be distributed over the rest pallets.
    let blocks = merge_rest_items(frm, rest_items, batch_specs)
        .map(entry => split_off_full_pallets(frm, entry, goods_height_limit, pallet))
        .filter(entry => entry.height > 0);

    let rest_pallet_packing;
    if(frm.doc.customer_palletize_by_batch || !goods_height_limit) {
        // Palletize batches individually => Use a trivial solution (one bin per merged entry)
        rest_pallet_packing = { bins: blocks.map((b, i) => [i]) };
    } else {
        // Put different items/batches together
        // TODO: For now we just do a 1D optimization of layer heights onto pallets.
        //       We could use a 3D packing library such as https://github.com/olragon/binpackingjs instead.
        rest_pallet_packing = pack_into_bins(blocks.map(b => b.height), blocks.length, goods_height_limit);
        if(!rest_pallet_packing.feasible) {
            frappe.msgprint(__("Error: No packing found for rest pallets"));
            return;
        }
    }

    // Calculate specs of each rest pallet
    for (var bin of rest_pallet_packing.bins) {
        if(bin.length == 0) {
            continue;
        }
        let height = pallet.pallet_base_height;
        let net_weight = 0;
        let gross_weight = pallet.pallet_tare;
        let item_names = [];
        // Sum up heights/weights of the blocks assigned to this pallet
        for (var block_idx of bin) {
            let block = blocks[block_idx];
            height += block.height;
            net_weight += block.net_weight;
            gross_weight += block.gross_weight;
            block.item_names.forEach(n => { if(!item_names.includes(n)) { item_names.push(n); } });
        }
        add_pallets(frm, {
            pallet_length: pallet.pallet_length,
            pallet_width: pallet.pallet_width,
            pallet_height: height,
            pallet_net_weight: net_weight,
            pallet_gross_weight: gross_weight,
            item_names: item_names
        }, 1);
    }
}


// Lowest of all maximum pallet heights that apply to a group of items: the customer's
// requirement and the limit defined in each item's Batch. Returns 0 if none is defined.
function get_max_pallet_height(frm, items, batch_specs) {
    let limits = [];
    if(frm.doc.customer_max_pallet_height > 0) {
        limits.push(frm.doc.customer_max_pallet_height);
    }
    for (var item of items) {
        let spec = batch_specs[item.batch];
        if(spec && spec.pallet_max_height > 0) {
            limits.push(spec.pallet_max_height);
        }
    }
    return limits.length > 0 ? Math.min(...limits) : 0;
}


// Pool the packages of those rest pallets that may be stacked into common layers, instead of
// treating each rest pallet as a solid block with a partly filled layer on top. Packages can
// share a layer if they are of the same Batch, or - unless the customer requires batches to be
// palletized individually - if their package specs are identical.
// Returns one entry per group of pooled packages.
function merge_rest_items(frm, rest_items, batch_specs) {
    let entries = new Map();
    for (var item of rest_items) {
        let spec = batch_specs[item.batch];
        if(!spec || !spec.package_weight || !spec.package_height || !spec.packages_per_layer) {
            frappe.show_alert({message: __("Row #{0}: Batch {1} has incomplete packaging details, its rest pallet cannot be optimized.", [item.idx, item.batch || '-']), indicator: 'orange'}, 30);
            spec = null;
        }
        let key;
        if(!spec) {
            key = "row:" + item.idx; // Unknown package specs: keep this rest pallet as it is
        } else if(frm.doc.customer_palletize_by_batch) {
            key = "batch:" + item.batch;
        } else {
            key = ["spec", spec.package_length, spec.package_width, spec.package_height, spec.package_tare, spec.package_weight, spec.packages_per_layer].join(":");
        }
        let entry = entries.get(key);
        if(!entry) {
            entry = { spec: spec, packages: 0, net_weight: 0, gross_weight: 0, height: 0, item_names: [] };
            entries.set(key, entry);
        }
        entry.packages += get_rest_packages(item, spec);
        entry.net_weight += item.rest_pallet_net_weight;
        // Gross weight of the goods only, i.e. without the pallet itself
        entry.gross_weight += item.rest_pallet_gross_weight - item.pallet_tare;
        if(!spec) {
            entry.height = item.rest_pallet_height - item.pallet_base_height;
        }
        if(!entry.item_names.includes(item.item_name)) {
            entry.item_names.push(item.item_name);
        }
    }
    return Array.from(entries.values());
}


// Number of packages on an item's rest pallet, derived from its net weight
// (the number of packages is ceil(quantity / package weight), cf. get_pallet_details_for_batch())
function get_rest_packages(item, spec) {
    if(!spec || !spec.package_weight) {
        return 0;
    }
    return Math.ceil(item.rest_pallet_net_weight / spec.package_weight - 1e-9);
}


// Stack the pooled packages of a merged entry into layers: create as many full pallets as the
// height limit allows and return the entry with the remaining, partly filled block of layers
function split_off_full_pallets(frm, entry, goods_height_limit, pallet) {
    if(!entry.spec) {
        return entry; // Unknown package specs: the block height is taken from the item as calculated by the server
    }
    let layers_per_pallet = goods_height_limit ? Math.floor(goods_height_limit / entry.spec.package_height) : 0;
    let packages_per_pallet = layers_per_pallet * entry.spec.packages_per_layer;
    let num_full_pallets = packages_per_pallet ? Math.floor(entry.packages / packages_per_pallet) : 0;
    if(num_full_pallets > 0) {
        // The pooled packages fill up whole pallets - these are added to the list right away.
        // The weights are distributed evenly over the packages rather than assuming the nominal
        // package weight, because the last package of every item row may be only partly filled.
        let full_net_weight = packages_per_pallet * entry.net_weight / entry.packages;
        let full_gross_weight = packages_per_pallet * entry.gross_weight / entry.packages;
        add_pallets(frm, {
            pallet_length: pallet.pallet_length,
            pallet_width: pallet.pallet_width,
            pallet_height: pallet.pallet_base_height + layers_per_pallet * entry.spec.package_height,
            pallet_net_weight: full_net_weight,
            pallet_gross_weight: full_gross_weight + pallet.pallet_tare,
            item_names: entry.item_names
        }, num_full_pallets);
        entry.packages -= num_full_pallets * packages_per_pallet;
        entry.net_weight -= num_full_pallets * full_net_weight;
        entry.gross_weight -= num_full_pallets * full_gross_weight;
    }
    entry.height = Math.ceil(entry.packages / entry.spec.packages_per_layer) * entry.spec.package_height;
    return entry;
}


// Add pallets to the consolidated list. If a pallet of identical specs is already listed,
// the number of that type of pallet is incremented instead.
function add_pallets(frm, specs, num_pallets) {
    let existing_pallet = frm.doc.pallets.find(p =>
        p.pallet_length == specs.pallet_length &&
        p.pallet_width == specs.pallet_width &&
        p.pallet_height == specs.pallet_height &&
        Math.abs(p.pallet_net_weight - specs.pallet_net_weight) < 0.001 &&
        Math.abs(p.pallet_gross_weight - specs.pallet_gross_weight) < 0.001
    );
    if(existing_pallet) {
        existing_pallet.num_pallets += num_pallets;
        // If some Items are not present in the items text, append them to it
        let listed_items = existing_pallet.items.split(", ");
        for (var item_name of specs.item_names) {
            if(!listed_items.includes(item_name)) {
                existing_pallet.items += ", " + item_name;
                listed_items.push(item_name);
            }
        }
        return existing_pallet;
    }
    let new_pallet = frm.add_child("pallets");
    new_pallet.num_pallets = num_pallets;
    new_pallet.pallet_length = specs.pallet_length;
    new_pallet.pallet_width = specs.pallet_width;
    new_pallet.pallet_height = specs.pallet_height;
    new_pallet.pallet_net_weight = specs.pallet_net_weight;
    new_pallet.pallet_gross_weight = specs.pallet_gross_weight;
    new_pallet.items = specs.item_names.join(", ");
    return new_pallet;
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
    if(['Int','Float'].includes((frappe.meta.get_field(frm.doctype, field) || []).fieldtype)) {
        fallback = 0;
    }
    if(!frm[field]) {
        frm.set_value(field, value || fallback);
    }
}