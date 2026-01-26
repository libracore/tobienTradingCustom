/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

frappe.ui.form.on('Claim', {
	setup(frm) {
	    if ( frm.doc.parent_claim ){
            frappe.db.set_value('Claim', frm.doc.parent_claim, 'is_group', 1)
                .then(r => {
                    let doc = r.message;
            });
	    }
	}
});