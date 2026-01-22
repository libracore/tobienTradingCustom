/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Sales Invoice', {
    before_save: function(frm) {
        apply_revenue_accounts(frm);

        // do not remind 5 days
    	cur_frm.set_value("exclude_from_payment_reminder_until",frappe.datetime.add_days(frm.doc.due_date, 5));
    },
    refresh: function(frm) {
        prepare_naming_series(frm);  // common function

        if (!frm.doc.__islocal) {
            cur_frm.set_df_property('company', 'read_only', 1);
        }
    },
    company: function(frm) {
        prepare_naming_series(frm);  // common function
    },
    is_return: function(frm) {
        prepare_naming_series(frm);  // common function
    }
});

function apply_revenue_accounts(frm) {
    // apply revenue accounts
    var items = frm.doc.items;
    items.forEach(function (item) {
        if ((item.income_account || "").startsWith("3200")) {
            if (frm.doc.debit_to.startsWith("1104")) {
                item.income_account = "3201 - Handelserlöse CHF - TTG";
            } else if (frm.doc.debit_to.startsWith("1105")) {
                item.income_account = "3202 - Handelserlöse USD - TTG";
            }
        }
    });
}