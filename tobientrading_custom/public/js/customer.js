/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Customer', {
    'refresh': function(frm) {

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
        if(frm.doc.__onload.addr_list && frm.doc.__onload.addr_list.length > 0) {
            frm.add_custom_button(__('Show on Google Maps'), function() {
                let address = frm.doc.__onload.addr_list.filter(f => f.is_primary_address);
                if(address.length > 0) {
                    address = address[0];
                } else {
                    address = frm.doc.__onload.addr_list[0];
                }
                let full_address = [
                    address.address_line1,
                    address.address_line2,
                    address.city,
                    address.state,
                    address.country,
                    address.pincode
                ].filter(Boolean).join(', ');
                let url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(full_address)}`;
                window.open(url, '_blank');
            });
        }
    }
});