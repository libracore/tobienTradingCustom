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

        frm.add_custom_button(__('Show on Google Maps'), function() {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Dynamic Link',
                    filters: {
                        link_doctype: 'Customer',
                        link_name: frm.doc.name,
                        parenttype: 'Address'
                    },
                    fields: ['parent'],
                    limit: 1
                },
                callback: function(res) {
                    if (res.message && res.message.length > 0) {
                        let address_name = res.message[0].parent;
                        frappe.db.get_doc('Address', address_name).then(address => {
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
                    } else {
                        frappe.show_alert({message: __('Maps: No address found.'), indicator: 'orange'});
                    }
                }
            });
        });
    }
});