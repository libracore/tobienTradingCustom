// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pallet Type", {
    before_save(frm) {
        // Ensure that length >= width
        let length = Math.max(frm.doc.length, frm.doc.width);
        let width = Math.min(frm.doc.length, frm.doc.width);
        frm.set_value("length", length);
        frm.set_value("width", width);
    }
});
