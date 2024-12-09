// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Measurement Parameter', {
	test_type: function(frm) {
		filter_subcategory_for_test_type(frm);
	}
});

function filter_subcategory_for_test_type(frm){
	frm.set_query("subcategory", function() {
		return {
			"filters": {
				"related_test_type": frm.doc.test_type
			}
		};
	});
}