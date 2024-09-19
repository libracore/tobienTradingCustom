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
	}
});

function import_from_pdf(type){
	console.log("importing data");
}

function import_from_excel(type){
	console.log("importing data");
}