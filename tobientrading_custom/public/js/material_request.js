/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function
        
        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }
    },
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    }
});
