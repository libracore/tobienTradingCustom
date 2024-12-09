// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate of Analysis', {
	refresh: function(frm) {
		populate_results_table(frm);
	},
	item: function(frm) {
		filter_batch_for_item(frm);
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

function filter_batch_for_item(frm){
	frm.set_query("batch_tt", function() {
		return {
			"filters": {
				"item": frm.doc.item
			}
		};
	});
}
