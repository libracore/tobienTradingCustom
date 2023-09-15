// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Opportunity", {
     refresh: function(frm) {
        render_activities_and_comments(frm);
    },
})

function render_activities_and_comments(frm) {
    frappe.call({
        method: "public.py.opportunity.get_activities_and_comments",
        args: {
            ref_doctype: frm.doc.doctype,
            ref_docname: frm.doc.name
        },
        callback: (r) => {
			if (!r.exc) {
				var activities_html = frappe.render_template('activities_and_comments_template', {
					activities: r.message.activities,
				});
				
				$(frm.fields_dict['custom_all_activities_html'].wrapper).html(activities_html)
			}
        }
    });
}

