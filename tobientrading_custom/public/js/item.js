/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

try {
    cur_frm.dashboard.add_transactions([
        {
            'label': 'TDS',
            'items': ['Technical Data Sheet']
        }
    ]);
} catch { /* do nothing for older versions */ }

frappe.ui.form.on('Item', {
    refresh: function(frm) {
        
    }
});
