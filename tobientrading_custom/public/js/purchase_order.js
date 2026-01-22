/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function

        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }
    },
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    loading_address: function(frm) {
        if (frm.doc.loading_address) {
            // fetch_tax_category(frm);
        }
    },
    before_save: function(frm) {
        if (frm.doc.__islocal) {
            // fetch_tax_category(frm);
        }
    },
    refresh: function(frm) {
        // shipping_address-Query
        setTimeout(function() {
            frm.fields_dict.shipping_address.get_query = function(doc) {
                return {
                    filters: {
                        'is_shipping_address': 1
                    }
                };
            };
        }, 1000);

        // Custom Button nur wenn Name gesetzt
        if (frm.doc.name && !frm.is_new() && (frm.doc.docstatus === 0 || frm.doc.docstatus === 1)) {
            frm.add_custom_button(__('Batch erstellen'), function () {
                frappe.call({
                    method: 'create_batches_from_po',
                    args: {
                        purchase_order: frm.doc.name
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

});
