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
    },

    packaging_spec(frm) {
        update_pallet_weight(frm);
    },

    package_weight(frm) {
        update_pallet_weight(frm);
    }
});


function update_pallet_weight(frm) {
    frappe.db.get_value("Supplier Packaging Spec", frm.doc.packaging_spec, "packages_per_pallet").then(r => {
        if(r.message) {
            frm.set_value("net_weight_per_pallet", r.message.packages_per_pallet * frm.doc.package_weight);
        }
    });
}