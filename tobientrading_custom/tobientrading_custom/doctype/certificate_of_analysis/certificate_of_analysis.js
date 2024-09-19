// Copyright (c) 2024, vanessa bualat and contributors
// For license information, please see license.txt

frappe.ui.form.on('Certificate of Analysis', {
	refresh: function(frm) {
		frm.add_custom_button(__("GBA PDF"), function(){
			import_from_pdf("GBA");
		}, __("Import from"));
		frm.add_custom_button(__("GBA Excel"), function(){
			import_from_excel("GBA");
		}, __("Import from"));
	}
});

function import_from_pdf(type){
	console.log("importing data");
}

function import_from_excel(type){
	console.log("importing data");
}