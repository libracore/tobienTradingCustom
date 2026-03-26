/* Copyright (C) libracore, 2026
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Batch', {
    refresh(frm) {
        frm.set_query('packaging_spec', function(doc, cdt, cdn) {
            return {
                filters: { supplier: doc.supplier }
            };
        });
    }
});