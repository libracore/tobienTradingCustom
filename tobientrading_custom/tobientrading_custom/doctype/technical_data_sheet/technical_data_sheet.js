// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Technical Data Sheet', {
	item_code: function(frm) {
	    if (frm.doc.item_code) {
    	    frappe.call({
                "method": "frappe.client.get",
                "args": {
                    "doctype": "Item",
                    "name": frm.doc.item_code
                },
                "callback": function(response) {
                    var item = response.message;
                    cur_frm.clear_table("origins");
                    for (var i = 0; i < item.origins.length; i++) {
                        var child = cur_frm.add_child('origins');
                        frappe.model.set_value(child.doctype, child.name, 'country_of_origin', item.origins[i].country_of_origin);
                    }
                    cur_frm.refresh_field('origins');
                    cur_frm.set_value("country_of_origin", item.country_of_origin);
                }
            });
	    }
    }
});