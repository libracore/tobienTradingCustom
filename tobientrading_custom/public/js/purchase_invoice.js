/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function

        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }

        if (frm.doc.items) {
            check_fetch_delivery_dates(frm);
        }

        // always set posting date/time
        cur_frm.set_value("set_posting_time", 1);

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

    before_save: function(frm) {
        apply_expense_accounts(frm);

        // on initial save, check purchase tax category from loading or supplier address
        if (frm.doc.__islocal) {
            // fetch_tax_category(frm);
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

    supplier_address: function(frm) {
        /* setTimeout(function () {
            if (frm.doc.loading_address || frm.doc.supplier_address) {
                fetch_tax_category(frm);
            }
        }, 4000); */
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


function check_fetch_delivery_dates(frm) {
    // loop through items
    for (var i = 0; i < frm.doc.items.length; i++) {
        // check if there is a purchase receipt and no delivery date
        if ((frm.doc.items[i].purchase_receipt) && (!frm.doc.items[i].delivery_date)) {
            // fetch delivery date from purchase receipt
            frappe.call({
                "method": "frappe.client.get",
                "args": {
                    "doctype": "Purchase Receipt",
                    "name": frm.doc.items[i].purchase_receipt
                },
                "async": false,
                "callback": function(response) {
                    var purchase_receipt = response.message;
                    if (purchase_receipt) {
                        frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, "delivery_date", purchase_receipt.posting_date);
                    }
                }
            });
        }
    }
}

function apply_expense_accounts(frm) {
    // apply expense accounts
    var items = frm.doc.items;
    items.forEach(function (item) {
        if (item.expense_account.startsWith("4200")) {
            if (frm.doc.credit_to.startsWith("2005")) {
                item.expense_account = "4201 - Handelswarenaufwand CHF - TTG";
            } else if (frm.doc.credit_to.startsWith("2006")) {
                item.expense_account = "4203 - Handelswarenaufwand USD - TTG";
            }
        }
    });
}

function fetch_tax_category(frm) {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Address",
            "name": (frm.doc.loading_address || frm.doc.supplier_address)
        },
        "async": false,
        "callback": function(response) {
            var address = response.message;
            frappe.show_alert("Ready " + address.tax_category_purchase);
            cur_frm.set_value("tax_category", address.tax_category_purchase);
        }
    });

}