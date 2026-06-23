/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function

        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }

        // delayed: override shipping address filter and upstream default
        setTimeout(function() {
            cur_frm.fields_dict.shipping_address.get_query = function(doc) {
                return {
                    filters: {
                        'is_shipping_address': 1
                    }
                };
            };

            if ((frm.doc.__islocal) && (frm.doc.items)) {
                // frappe will reset the shipping address to the company default, which is wrong - reset to upstream
                reset_shipping_address(frm);
            }
        }, 1000);
    },
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    before_submit: function(frm) {
        if(frm.doc.items.length > 0) {
            confirm_packspec_for_row(frm, 0);
        }
    }
});

function reset_shipping_address(frm) {
    if (frm.doc.items.length > 0) {
        var po = frm.doc.items[0].purchase_order;
        if (po) {
            frappe.call({
                "method": "frappe.client.get",
                "args": {
                    "doctype": "Purchase Order",
                    "name": po
                },
                "callback": function(response) {
                    var po_doc = response.message;
                    cur_frm.set_value("shipping_address", po_doc.shipping_address);
                }
            });
        }
    }
}

// Show a dialog to confirm packaging specs pulled from a Line Item's Batch.
// If a Purchase Receipt has several Line Items, this dialog is shown for each Line Item separately by means of a recursive function call.
function confirm_packspec_for_row(frm, row_no) {
    frappe.validated = false;
    let row = frm.doc.items[row_no];
    if(!row.batch_no) {
        frappe.db.get_value("Item", row.item_code, "has_batch_no").then(r => {
            if(r.message.has_batch_no) {
                frappe.show_alert({message: __("Row #{0}: Batch No is required for '{1}'", [row.idx, row.item_name]), title:__("Validation error"), indicator: 'red'}, 30);
                frm.fields_dict.items.grid.grid_rows[0].open_row_at_index(row.idx - 1);
                setTimeout(() => { frm.fields_dict.items.grid.open_grid_row.fields_dict.batch_no.wrapper.scrollIntoView(); }, 500);
            } else if(frm.doc.items.length - 1 > row_no) {
                confirm_packspec_for_row(frm, row_no + 1); // This row needs no Batch, continue with next one
            } else {
                do_submit(frm); // No more rows to process, ready to submit
            }
        });
        return;
    }
    frappe.db.get_list("Serial and Batch Bundle", {filters: [["Serial and Batch Entry","batch_no","=",row.batch_no]], limit: 1}).then(stock_transactions => {
        let has_transactions = (stock_transactions.length > 0);
        frappe.db.get_doc("Batch", row.batch_no).then(batch_doc => {
            let packspec_dialog = new frappe.ui.Dialog({
                title: __("Confirm packaging specs for row #{0}:<br>{1} (Batch #{2})", [row.idx, row.item_name, row.batch_no]),
                fields: [
                    {
                        fieldname: 'read_only_warning',
                        fieldtype: 'HTML',
                        options: has_transactions ? `<b>${__('NOTE: This Batch has transactions. Specs are read-only.')}</b>` : ''
                    },
                    {
                        fieldname: 'package_weight',
                        fieldtype: 'Float',
                        label: __('Package weight [kg]'),
                        default: batch_doc.package_weight,
                        reqd: true,
                        read_only: has_transactions,
                    },
                    {
                        fieldname: 'packaging_spec',
                        fieldtype: 'Link',
                        options: 'Supplier Packaging Spec',
                        label: __('Supplier Packaging Spec'),
                        default: batch_doc.packaging_spec,
                        reqd: true,
                        read_only: has_transactions,
                        onchange: () => {
                            frappe.db.get_doc("Supplier Packaging Spec", packspec_dialog.fields_dict.packaging_spec.value).then (ps => {
                                packspec_dialog.set_values({
                                    pallet_type: ps.pallet_type,
                                    pallet_max_height: ps.pallet_max_height,
                                    packaging_type: ps.packaging_type,
                                    package_tare: ps.package_tare,
                                    package_length: ps.package_length,
                                    package_width: ps.package_width,
                                    package_height: ps.package_height,
                                    packages_per_layer: ps. packages_per_layer,
                                    layers_per_pallet: ps.layers_per_pallet,
                                });
                            });
                        }
                    },
                    {
                        fieldname: 'sb0',
                        fieldtype: 'Section Break'
                    },
                    {
                        fieldname: 'update_packaging_spec',
                        fieldtype: 'Check',
                        default: true,
                        label: __('Update the linked supplier packaging spec to the values below'),
                        description: __('NOTE: Pallet details are not updated automatically')
                    },
                    {
                        fieldname: 'sb1',
                        fieldtype: 'Section Break',
                    },
                    {
                        fieldname: 'pallet_type',
                        fieldtype: 'Link',
                        read_only: has_transactions,
                        options: 'Pallet Type',
                        label: __('Pallet type'),
                        default: batch_doc.pallet_type,
                        reqd: true,
                        onchange: () => {
                            frappe.db.get_doc("Pallet Type", packspec_dialog.fields_dict.pallet_type.value).then (pt => {
                                packspec_dialog.set_values({
                                    pallet_tare: pt.tare,
                                    pallet_length: pt.length,
                                    pallet_width: pt.width,
                                    pallet_base_height: pt.height
                                });
                            });
                        }
                    },
                    {
                        fieldname: 'pallet_tare',
                        fieldtype: 'Float',
                        read_only: has_transactions,
                        label: __('Pallet tare [kg]'),
                        default: batch_doc.pallet_tare,
                        reqd: true,
                    },
                    {
                        fieldname: 'pallet_length',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Pallet length [cm]'),
                        default: batch_doc.pallet_length,
                        reqd: true,
                    },
                    {
                        fieldname: 'pallet_width',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Pallet width [cm]'),
                        default: batch_doc.pallet_width,
                        reqd: true,
                    },
                    {
                        fieldname: 'pallet_base_height',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Pallet base height [cm]'),
                        default: batch_doc.pallet_base_height,
                        reqd: true,
                    },
                    {
                        fieldname: 'pallet_max_height',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Max pallet height [cm]'),
                        default: batch_doc.pallet_max_height,
                        reqd: true,
                    },
                    {
                        fieldname: 'cb',
                        fieldtype: 'Column Break',
                    },
                    {
                        fieldname: 'packaging_type',
                        fieldtype: 'Link',
                        options: 'Packaging Type',
                        read_only: has_transactions,
                        label: __('Packaging type'),
                        default: batch_doc.packaging_type,
                        reqd: true,
                    },
                    {
                        fieldname: 'package_tare',
                        fieldtype: 'Float',
                        read_only: has_transactions,
                        label: __('Package tare [kg]'),
                        default: batch_doc.package_tare,
                        reqd: true,
                    },
                    {
                        fieldname: 'package_length',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Package length [cm]'),
                        default: batch_doc.package_length,
                        reqd: true,
                    },
                    {
                        fieldname: 'package_width',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Package width [cm]'),
                        default: batch_doc.package_width,
                        reqd: true,
                    },
                    {
                        fieldname: 'package_height',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Package height [cm]'),
                        default: batch_doc.package_height,
                        reqd: true,
                    },
                    {
                        fieldname: 'sb2',
                        fieldtype: 'Section Break',
                    },
                    {
                        fieldname: 'packages_per_layer',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Packages per layer'),
                        default: batch_doc.packages_per_layer,
                        reqd: true,
                    },
                    {
                        fieldname: 'cb2',
                        fieldtype: 'Column Break',
                    },
                    {
                        fieldname: 'layers_per_pallet',
                        fieldtype: 'Int',
                        read_only: has_transactions,
                        label: __('Layers per pallet'),
                        default: batch_doc.layers_per_pallet,
                        reqd: true,
                    },
                ],
                primary_action: (values) => {
                    packspec_dialog.hide();
                    let batch_modified = false;
                    for(let i=0; i < packspec_dialog.fields.length; i++) {
                        let field = packspec_dialog.fields[i];
                        if(values[field.fieldname] != field.default) {
                            batch_modified = true;
                            break;
                        }
                    }
                    if(batch_modified) {
                        frappe.call({
                            method: "tobientrading_custom.tobientrading_custom.utils.set_batch_packaging_specs",
                            args: {
                                batch: row.batch_no,
                                specs: values
                            },
                            callback: function(response) {
                                frappe.show_alert({message: __("Packaging specs updated"), indicator: "green"});
                                if(frm.doc.items.length - 1 > row_no) {
                                    confirm_packspec_for_row(frm, row_no + 1); // Done processing this row's packaging specs, continue with next one
                                }
                                else {
                                    do_submit(frm); // No more rows to process, ready to submit
                                }
                            },
                            error: function(message) {
                                frappe.msgprint(__("An error occurred while saving updated packaging specs"));
                            }
                        });
                    } else {
                        if(frm.doc.items.length - 1 > row_no) {
                            confirm_packspec_for_row(frm, row_no + 1); // Nothing to update, continue with next row
                        }
                        else {
                            do_submit(frm); // No more rows to process, ready to submit
                        }

                    }
                },
                primary_action_label: __("Save"),
                secondary_action: () => {
                    packspec_dialog.hide();
                },
                secondary_action_label: __("Cancel")
            });
            packspec_dialog.show();
        });
    });
}


function do_submit(frm) {
    frm.save(
        "Submit",
        function (r) {
            if (!r.exc) {
                frappe.utils.play_sound("submit");
                frm.script_manager
                    .trigger("on_submit")
                    .then(() => {
                        if (frappe.route_hooks.after_submit) {
                            let route_callback =
                                frappe.route_hooks.after_submit;
                            delete frappe.route_hooks.after_submit;
                            route_callback(frm);
                        }
                    });
            }
        }
    );
}