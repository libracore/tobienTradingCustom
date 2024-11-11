// Copyright (c) 2024, vanessa bualat and contributors
// For license information, please see license.txt
document.addEventListener('DOMContentLoaded', function () {
	// dynamically load the xlsx library
	var xlsx = document.createElement('script');
	xlsx.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.16.9/xlsx.full.min.js';
	document.head.appendChild(xlsx);
});

frappe.ui.form.on('Certificate of Analysis', {
	refresh: function(frm) {
		frm.add_custom_button("GBA Excel", function(){
			var gba_config = {
				"coa": cur_frm.doc.name,
				"results": cur_frm.doc.results
			}
			import_from_excel(gba_config);
		}, "Import from");

		populate_results_table(frm);
	}
});

function import_from_excel(config){
	var input = document.createElement("input");
	input.type = 'file';
	input.accept = '.xls,.xlsx';

	// Add an event listener to listen for when a file is selected
	input.addEventListener('change', function (event) {
		var file = event.target.files[0];
		if (file) {
			read_file(file, config);
		} else {
			frappe.msgprint("No file selected");
		}
	});
	input.click();
}

function read_file(file, config){
	var reader = new FileReader();
	reader.addEventListener('load', function (event) {
		var contents = event.target.result;
		extract_data(contents, config);
	});
	reader.onerror = function (event) {
		frappe.msgprint("Error reading file");
	};
	reader.readAsBinaryString(file);
}

function extract_data(contents, config){
	var workbook = XLSX.read(contents, {type: 'binary'});
	var sheet_name_list = workbook.SheetNames[0];
	var worksheet = workbook.Sheets[sheet_name_list];
	var data = XLSX.utils.sheet_to_json(worksheet, {header: 1});
	console.log(data);
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
