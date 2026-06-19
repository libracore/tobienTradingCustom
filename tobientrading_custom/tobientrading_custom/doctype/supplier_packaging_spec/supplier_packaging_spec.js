// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on("Supplier Packaging Spec", {
    refresh(frm) {
        frm.set_query('supplier', function(doc) {
            return {
                filters: {
                    'disabled': 0
                }
            };
        });
        frm.set_query("item", "items", () => {
            return {
                filters: {has_variants: 0}
            };
        });
    },

    pallet_type(frm) {
        update_description(frm);
    },

    package_length(frm) {
        ensure_length_width_order(frm);
        update_description(frm);
    },
    package_width(frm) {
        ensure_length_width_order(frm);
        update_description(frm);
    },
    package_height(frm) {
        update_description(frm);
    },
    packaging_type(frm) {
        update_description(frm);
    },

    btn_palletize(frm) {
        set_optimal_pallet_details(frm);
    },
    packages_per_layer(frm) {
        update_num_packages(frm);
    },
    layers_per_pallet(frm) {
        update_num_packages(frm);
    },
});

frappe.ui.form.on("Supplier Packaging Item Assignment", {
    nominal_package_weight(frm, cdt, cdn) {
        update_pallet_net_weights(frm, locals[cdt][cdn].idx);
    },
});


function ensure_length_width_order(frm) {
    if(frm.doc.package_length && frm.doc.package_width) {
        // Ensure that package length >= package width
        let package_length = Math.max(frm.doc.package_length, frm.doc.package_width);
        let package_width = Math.min(frm.doc.package_length, frm.doc.package_width);
        frm.set_value("package_length", package_length);
        frm.set_value("package_width", package_width);
    }
}

function set_optimal_pallet_details(frm) {

    if(frm.doc.package_length && frm.doc.package_width && frm.doc.pallet_type && frm.doc.pallet_max_height && frm.doc.package_height) {
        frappe.call({
            method: 'tobientrading_custom.tobientrading_custom.doctype.pallet_type.pallet_type.get_pallet_details_from_type',
            args: {
                pallet_type: frm.doc.pallet_type,
                pallet_max_height: frm.doc.pallet_max_height,
                package_length: frm.doc.package_length,
                package_width: frm.doc.package_width,
                package_height: frm.doc.package_height
            },
            callback: function(r) {
                let pallet_details = r.message;
                frm.set_value("packages_per_layer", pallet_details.packages_per_layer);
                frm.set_value("layers_per_pallet", pallet_details.layers_per_pallet);
                update_num_packages(frm);
            }
        });
    } else {
        frappe.msgprint(__("Please fill out all fields to proceed."),__("Incomplete data"));
    }
}


function update_num_packages(frm) {
    frm.set_value("packages_per_pallet", frm.doc.packages_per_layer * frm.doc.layers_per_pallet).then(() => {
        update_pallet_net_weights(frm);
        update_description(frm);
    });
}


function update_description(frm) {
    // e.g. "SUP-00043 - Europallet with 5 layers of 8 Carton with Inliner 40x30x35cm"
    let description = `${frm.doc.supplier} - ${frm.doc.pallet_type} with ${frm.doc.layers_per_pallet} layers of ${frm.doc.packaging_type} ${frm.doc.package_length}×${frm.doc.package_width}×${frm.doc.package_height} cm`;
    frm.set_value("description", description);
}


function update_pallet_net_weights(frm, idx=0){
    let rows = frm.doc.items;
    if(idx) {
        rows = [rows[idx-1]];
    }
    for(r of rows) {
        frappe.model.set_value(r.doctype, r.name, "nominal_net_weight_per_pallet", r.nominal_package_weight * frm.doc.packages_per_pallet);
    }
}