/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Address', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {  // Button nur bei gespeicherter Adresse anzeigen
            frm.add_custom_button(__('Google Maps'), function() {
                let full_address = [
                    frm.doc.address_line1,
                    frm.doc.address_line2,
                    frm.doc.city,
                    frm.doc.state,
                    frm.doc.country,
                    frm.doc.pincode
                ].filter(Boolean).join(', ');

                let url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(full_address)}`;
                window.open(url, '_blank');
            });
        }
    }
});