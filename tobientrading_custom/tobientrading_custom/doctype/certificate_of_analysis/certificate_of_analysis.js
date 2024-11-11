// Copyright (c) 2024, vanessa bualat and contributors
// For license information, please see license.txt
frappe.ui.form.on('Certificate of Analysis', {
	refresh: function(frm) {
		populate_results_table(frm);
	}
});

function populate_results_table(fm){
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.get_results",
		'args': {
			'coa': cur_frm.doc.name 
		},
		'callback': function(response){
			if (response.message) {
				cur_frm.set_df_property('results','options', response.message);
			}
		}
	})
}
