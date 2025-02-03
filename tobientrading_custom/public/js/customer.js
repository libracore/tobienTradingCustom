/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Customer', {
    'refresh': function(frm) {
        console.log("refresh");
        frappe.call({
            'method': 'tobientrading_custom.tobientrading_custom.utils.get_emergency_contact', 
            'args': {
                'dt': cur_frm.doc.doctype, 
                'dn': cur_frm.doc.name
            }, 
            'callback': function(response) { 
                let contacts = response.message;
                console.log(contacts);
                if (contacts.length > 0) {
                    for (let i = 0; i < contacts.length; i++) {
                        cur_frm.dashboard.add_comment( 
                            (__('Emergency Contact') 
                            + ": " + (contacts[i].first_name || "")
                            + " " + (contacts[i].last_name || "")
                            + ": " + (contacts[i].phone || "")), 'blue', true);
                    }
                }
            }
        });
    }
});
