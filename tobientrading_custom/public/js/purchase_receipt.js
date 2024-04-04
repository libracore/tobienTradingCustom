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
