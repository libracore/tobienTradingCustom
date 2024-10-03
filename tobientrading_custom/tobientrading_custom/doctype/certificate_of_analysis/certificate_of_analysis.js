// Copyright (c) 2024, vanessa bualat and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate of Analysis', {
	refresh: function(frm) {
		frm.add_custom_button("GBA PDF", function(){
			import_from_pdf("GBA");
		}, "Import from");
		frm.add_custom_button("GBA Excel", function(){
			import_from_excel("GBA");
		}, "Import from");

		populate_results_table(frm);
	}
});

function import_from_pdf(type){
	console.log("importing data");
}

function import_from_excel(type){
	console.log("importing data");
}

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