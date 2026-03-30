/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Purchase Order', {
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    loading_address: function(frm) {
        if (frm.doc.loading_address) {
            // fetch_tax_category(frm);
        }
    },
    validate(frm) {
        for(let i=0; i < frm.doc.items.length; i++) {
            if(!frm.doc.items[i].package_weight) {
                frappe.msgprint(__("Item #{0}: Package weight is required.", [frm.doc.items[i].idx]), __("Validation error"));
                frappe.validated = false;
                break;
            }
        }
    },
    before_save: function(frm) {
        if (frm.doc.__islocal) {
            // fetch_tax_category(frm);
        }
    },
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function

        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }

        frm.set_query('shipping_address', function(doc) {
            return {
                filters: {
                    'is_shipping_address': 1
                }
            };
        });
        frm.set_query('packaging_spec', "items", function(doc, cdt, cdn) {
            return {
                filters: { supplier: doc.supplier }
            };
        });

        // Custom Button nur wenn Name gesetzt
        if (frm.doc.name && !frm.is_new() && (frm.doc.docstatus === 0 || frm.doc.docstatus === 1)) {
            frm.add_custom_button(__('Batch erstellen'), function () {
                frappe.call({
                    method: 'tobientrading_custom.tobientrading_custom.utils.create_batches_from_po',
                    args: {
                        po_no: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});

frappe.ui.form.on('Purchase Order Item', {
    packaging_spec(frm, cdt, cdn) {
        if(locals[cdt][cdn].packaging_spec) {
            frappe.db.get_doc("Supplier Packaging Spec", locals[cdt][cdn].packaging_spec).then(pspec_doc => {
                item_assignment = pspec_doc.items.filter(a => a.item == locals[cdt][cdn].item_code);
                if(item_assignment.length > 0) {
                    item_assignment = item_assignment[0];
                    if(!item_assignment.batch_specific_package_weight) {
                        // Load package weight from specs unless it is batch-specific
                        frappe.model.set_value(cdt, cdn, "package_weight", item_assignment.nominal_package_weight);
                    }
                    else {
                        frappe.show_alert({message: __("Package weight is defined to be batch-specific here, please enter a weight manually.<br> Nominal weight: {0} kg", [item_assignment.nominal_package_weight]), indicator: "blue"}, 30);
                    }
                }
                else {
                    frappe.show_alert({message: __("The selected packaging spec contains no details for this Item. If you want to use it with this Item anyway, please set the package weight manually."), indicator: "orange"}, 30);
                }
            });
        }
    }

});

function fetch_tax_category(frm) {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Address",
            "name": frm.doc.loading_address
        },
        "async": false,
        "callback": function(response) {
            var address = response.message;
            frm.set_value("tax_category", address.tax_category_purchase);
        }
    });
}
