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
	items_add: function(frm, cdt, cdn) {
		set_blanket_rate(frm, cdt, cdn);
	},
	validate: function(frm) {
		frm.doc.items.forEach((row) => {
			set_blanket_rate(frm, row.doctype, row.name);
		});
	},
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    after_save: function(frm) {
	   frappe.call({
            "method": "frappe.client.get",
            "args": {
                "doctype": "Customer",
                "name": frm.doc.customer
            },
            "async": false,
            "callback": function(response) {
                var customer = response.message;
                console.log(response);
                if(customer.customer_label_requierments == 1){
                        frappe.msgprint({
                        title: __('Label Required<br>'),
                        indicator: 'black',
                        message: __("<b>Label für die Gebinde:</b><br><div style='border-style: solid; border-color: red; border-width: 1rem; padding: 1rem;background-color: #0053e2;color:white'>" + customer.customer_label_on_packaging_requiered_.replaceAll("\n", "<br>") + "</div>")
                    });
                }
            }
        });
        frappe.call({
            "method": "frappe.client.get",
            "args": {
                "doctype": "Customer",
                "name": frm.doc.customer
            },
            "async": false,
            "callback": function(response) {
                var customer = response.message;
                console.log(response);
                if(customer.customer_label_on_pallet_requiered == 1){
                        frappe.msgprint({
                        title: __('Label Required<br>'),
                        indicator: 'black',
                        message: __("<b>Label für die Palette:</b><br><div style='border-style: solid; border-color: red; border-width: 1rem; padding: 1rem;background-color: #0053e2;color:white'>" + customer.customer_label_on_pallet_requiered_text.replaceAll("\n", "<br>") + "</div>")
                    });
                }
            }
        });
	}
});

frappe.ui.form.on('Sales Order Item', {
	blanket_order_rate: function(frm, cdt, cdn) {
		set_blanket_rate(frm, cdt, cdn);
	},
	item_code: function(frm, cdt, cdn) {
		set_blanket_rate(frm, cdt, cdn);
	}
});


// Blanket Order Rate in den Listenpreis schreiben, damit darauf Rabatte aus Pricing Rules angewendet werden
function set_blanket_rate(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row) return;

    if(row.blanket_order_rate && row.blanket_order_rate != row.price_list_rate){
		frappe.model.set_value(cdt, cdn, 'price_list_rate', row.blanket_order_rate);
		frappe.show_alert({message: __("Row {0}: List price was set to Blanket Order price", [row.idx])}, 10);
	}
}