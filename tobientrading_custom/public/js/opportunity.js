// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Opportunity", {
     refresh: function(frm) {
        render_activities_and_comments(cur_frm);
    },
})

function render_activities_and_comments(frm) {
		console.log("render_activities_and_comments")
		frappe.call({
			method: "erpnext.crm.utils.get_activities",
			args: {
				ref_doctype: frm.doc.doctype,
				ref_docname: frm.doc.name
			},
			callback: (r) => {
				if (!r.exc) {
					
					console.log("r")
					//~ cur_frm.set_df_property('custom_all_activities_html','options', activities_html);
				}
			}
		});
}
