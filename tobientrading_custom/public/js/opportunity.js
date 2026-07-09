// Copyright (c) 2026, libracore AG and contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Opportunity", {
     refresh: function(frm) {
        display_comment_box();
    }
})

function display_comment_box() {
    setTimeout(() => {
        $("#page-Opportunity .comment-box").show();
    }, 100);
}
