// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate of Analysis Result', {
	parameter: function(frm) {
		fetch_test_type_and_subcategory(frm);
	}
});


function fetch_test_type_and_subcategory(frm){
	console.log(frm.doc.parameter);
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis_result.certificate_of_analysis_result.get_test_type_and_subcategory",
		'args': {
			'parameter': frm.doc.parameter
		},
		'callback': function(response){
			console.log(response.message);
			if (response.message) {
				frm.set_value('test_type', response.message.test_type);
				frm.set_value('test_type_subcategory', response.message.subcategory);
			}
		}
	})
}