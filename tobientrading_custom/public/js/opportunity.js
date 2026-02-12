// Copyright (c) 2026, libracore AG and contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Opportunity", {
     refresh: function(frm) {
        display_comment_box();
    }
})

function display_comment_box() {
    setTimeout(() => {
        const comment_box = document.querySelector(".comment-box");
        if (comment_box) {
            comment_box.style.display = "block";
        }
    }, 100);
}


