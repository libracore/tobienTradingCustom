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
	}
});