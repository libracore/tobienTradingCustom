/* Copyright (C) libracore, 2026
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        if (frm.doc.name && !frm.is_new() && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Charge anlegen'), function () {
                create_batch(frm);
            });
        }
    }
});

function create_batch(frm) {
    if (!frm.doc.production_item) {
        frappe.msgprint(__("No production item set on this Work Order."), __("Validation error"));
        return;
    }
    if (!frm.doc.contract_processing_supplier) {
        frappe.msgprint(__("Please set the Contract Processing Supplier first."), __("Validation error"));
        return;
    }

    // Find packaging specs for this item / supplier (cf. purchase_order.js)
    frappe.db.get_list("Supplier Packaging Spec", {
        filters: [
            ["supplier", "=", frm.doc.contract_processing_supplier],
            ["Supplier Packaging Item Assignment", "item", "=", frm.doc.production_item]
        ],
        limit: 2
    }).then(specs => {
        if (specs.length === 0) {
            frappe.msgprint(__("No packaging spec found for item {0} and supplier {1}.",
                [frm.doc.production_item, frm.doc.contract_processing_supplier]), __("Validation error"));
        } else if (specs.length === 1) {
            create_mo_batch(frm, specs[0].name);
        } else {
            // More than one spec: let the user pick one (filtered by supplier)
            frappe.prompt([
                {
                    fieldname: 'packaging_spec',
                    label: __('Packaging Spec'),
                    fieldtype: 'Link',
                    options: 'Supplier Packaging Spec',
                    reqd: 1,
                    get_query: function () {
                        return {
                            filters: [
                                ["supplier", "=", frm.doc.contract_processing_supplier],
                                ["Supplier Packaging Item Assignment", "item", "=", frm.doc.production_item]
                            ]
                        };
                    }
                }
            ], function (values) {
                create_mo_batch(frm, values.packaging_spec);
            }, __('Charge anlegen'), __('Erstellen'));
        }
    });
}

function create_mo_batch(frm, packaging_spec) {
    frappe.call({
        method: 'tobientrading_custom.tobientrading_custom.utils.create_mo_batch',
        args: {
            work_order: frm.doc.name,
            packaging_spec: packaging_spec
        },
        freeze: true,
        freeze_message: __("Creating batch ..."),
        callback: function (r) {
            if (r.message) {
                frappe.msgprint(r.message);
                frm.reload_doc();
            }
        }
    });
}
