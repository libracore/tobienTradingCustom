/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function
        
        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }
    },
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    on_submit: function(frm) {
        attach_tds_pdfs(frm);
    }
});

function attach_tds_pdfs(frm) {
    frappe.call({
        'method': 'tobientrading_custom.tobientrading_custom.utils.attach_tds_pdfs',
        'args': {
            'sales_order': frm.doc.name
        }
    });
}
