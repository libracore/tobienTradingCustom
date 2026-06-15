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
    before_save(frm) {
        if (frm.doc.has_variants) {
            var origins = [];
            if (frm.doc.origins) {
                for (var i = 0; i < frm.doc.origins.length; i++) {
                    origins.push(frm.doc.origins[i].country_of_origin);
                }
            }
            // apply origins to variants
            frappe.call({
                "method": "tobientrading_custom.tobientrading_custom.utils.apply_origins_to_variants",
                "args": {
                    "template_item_code": frm.doc.name,
                    "origins": origins
                }
            });
        }
    },
    refresh(frm) {
        if ((frm.doc.variant_of) && ((!frm.doc.origins) || (frm.doc.origins.length === 0))) {
            // pull origins from template
            if (frm.doc.variant_of) {
                frappe.call({
                    "method": "frappe.client.get",
                    "args": {
                        "doctype": "Item",
                        "name": frm.doc.variant_of
                    },
                    "callback": function(response) {
                        var item = response.message;
                        cur_frm.clear_table("origins");
                        for (var i = 0; i < item.origins.length; i++) {
                            var child = cur_frm.add_child('origins');
                            frappe.model.set_value(child.doctype, child.name, 'country_of_origin', item.origins[i].country_of_origin);
                        }
                        cur_frm.refresh_field('origins');
                    }
                });
            }
        }

        if(!frm.doc.__islocal) {
            get_batch_info(frm);
        }
    },
});

frappe.ui.form.on('Item Supplier', {
    btn_packaging_details(frm, cdt, cdn) {
        frappe.set_route("List", "Supplier Packaging Spec", {supplier: locals[cdt][cdn].supplier, item: frm.doc.item_code});
    }
});


function get_batch_info(frm) {
    frappe.call({
        method: 'tobientrading_custom.tobientrading_custom.utils.get_batch_info',
        args: {
            item_code: frm.doc.item_code
        },
        callback: function(response) {
            var batches = response.message;
            if ((batches) && (batches.length > 0)) {
                let html = `
                    <table class="table" style="width: 100%;">
                        <tr><th>${__("Batch")}
                        </th><th>${__("Packaging")}
                        </th><th>${__("Current stock")}
                        </th></tr>`;
                for (let i=0; i < batches.length; i++) {
                    let packaging_info = __('N/A');
                    if(batches[i].layers_per_pallet) {
                        let qty_per_pallet = batches[i].packages_per_pallet * batches[i].package_weight;
                        packaging_info = `${batches[i].packages_per_pallet}x ${batches[i].package_weight} ${batches[i].stock_uom} = ${qty_per_pallet} ${batches[i].stock_uom}`;
                    }
                    html += `
                        <tr><td><a href="/app/batch/${batches[i].batch_no}">${batches[i].batch_no}</a></td>
                            <td>${packaging_info}</td>
                            <td>${batches[i].qty} ${batches[i].stock_uom}</td>`;
                }
                html += "</table>";
                frm.set_df_property('batch_overview_html','options',html);
            } else if (batches) {
                frm.set_df_property('batch_overview_html','options',__('<div style="text-align:center;margin-bottom:20px">No batches available.</div>'));
            }
        }
    });
}
