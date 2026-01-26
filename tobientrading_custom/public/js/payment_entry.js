/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Payment Entry', {
	refresh(frm) {
		frm.add_custom_button(__("Mietaufwand"), function() {
            rent(frm);
        });
        frm.add_custom_button(__("Währungsaufwand"), function() {
            currency(frm);
        });

        currency_hack(frm);
	}
});

function add_deduction(account, cost_center, amount) {
    var child = cur_frm.add_child('deductions');
    frappe.model.set_value(child.doctype, child.name, 'account', account);
    frappe.model.set_value(child.doctype, child.name, 'cost_center', cost_center);
    frappe.model.set_value(child.doctype, child.name, 'amount', amount);
}


function rent(frm) {
    add_deduction("6000 - Raumaufwand - TTG", "Haupt - TTG", frm.doc.unallocated_amount || frm.doc.difference_amount);
    cur_frm.refresh_field('deductions');
}

function currency(frm) {
    var expense = frm.doc.unallocated_amount || frm.doc.difference_amount;
    if (expense > 0) {
        add_deduction("6949 - Währungsverluste - TTG", "Haupt - TTG", expense);
    } else {
        add_deduction("6999 - Währungsgewinne - TTG", "Haupt - TTG", expense);
    }
    cur_frm.refresh_field('deductions');
}

function currency_hack(frm) {
    // hack: force-load exchange rates
    if (frm.doc.docstatus === 0) {
        frappe.call({
        	'method': 'erpnext.setup.utils.get_exchange_rate',
        	'args': {
        		'from_currency': cur_frm.doc.paid_from_account_currency,
                'to_currency': (cur_frm.doc.company_currency || "EUR"),
                'transaction_date': cur_frm.doc.posting_date
        	},
        	'callback': function(r) {
        	    console.log("source: "+ r.message);
        		cur_frm.set_value("source_exchange_rate", r.message);
        	}
        });
        frappe.call({
        	'method': 'erpnext.setup.utils.get_exchange_rate',
        	'args': {
        		'from_currency': cur_frm.doc.paid_to_account_currency,
                'to_currency': (cur_frm.doc.company_currency || "EUR"),
                'transaction_date': cur_frm.doc.posting_date
        	},
        	'callback': function(r) {
        	    console.log("target: "+ r.message);
        		cur_frm.set_value("target_exchange_rate", r.message);
        	}
        });
    }
}