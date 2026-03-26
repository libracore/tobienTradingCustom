// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on("Supplier Packaging Spec", {
    refresh(frm) {
    },

    pallet_type(frm) {
        update_calculations(frm);
    },
    pallet_max_height(frm) {
        update_calculations(frm);
    },

    packaging_type(frm) {
        update_description(frm);
    },
    package_length(frm) {
        if(!frm.updating_calculations) {
            update_calculations(frm);
        }
    },
    package_width(frm) {
        if(!frm.updating_calculations) {
            update_calculations(frm);
        }
    },
    package_height(frm) {
        update_calculations(frm);
    },

    before_save(frm) {
        update_calculations(frm);
    },
});


function update_calculations(frm) {

    if(frm.doc.package_length && frm.doc.package_width && frm.doc.pallet_type && frm.doc.pallet_max_height && frm.doc.package_height) {

        frm.updating_calculations = true;

        // Ensure that package length >= package width
        let package_length = Math.max(frm.doc.package_length, frm.doc.package_width);
        let package_width = Math.min(frm.doc.package_length, frm.doc.package_width);
        frm.set_value("package_length", package_length);
        frm.set_value("package_width", package_width);

        frm.updating_calculations = false;

        frappe.call({
            method: 'tobientrading_custom.tobientrading_custom.doctype.pallet_type.pallet_type.get_pallet_details_from_type',
            args: {
                pallet_type: frm.doc.pallet_type,
                pallet_max_height: frm.doc.pallet_max_height,
                package_length: package_length,
                package_width: package_width,
                package_height: frm.doc.package_height
            },
            callback: function(r) {
                let pallet_details = r.message;
                frm.set_value("packages_per_layer", pallet_details.packages_per_layer);
                frm.set_value("layers_per_pallet", pallet_details.layers_per_pallet);
                frm.set_value("packages_per_pallet", pallet_details.packages_per_pallet);
                update_description(frm);
            }
        });
    }
}


function update_description(frm) {
    // e.g. "SUP-00043 - Europallet with 5 layers of 8 Carton with Inliner 40x30x35cm"
    let description = `${frm.doc.supplier} - ${frm.doc.pallet_type} with ${frm.doc.layers_per_pallet} layers of ${frm.doc.packaging_type} ${frm.doc.package_length}×${frm.doc.package_width}×${frm.doc.package_height} cm`;
    frm.set_value("description", description);
}