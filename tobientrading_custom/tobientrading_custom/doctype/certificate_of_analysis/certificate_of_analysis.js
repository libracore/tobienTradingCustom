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
    var tableBody = document.getElementById("results-table").getElementsByTagName('tbody')[0];
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.get_results",
		'args': {
			'coa': cur_frm.doc.name 
		},
		'callback': function(response){
			if (response.message) {
				console.log(response.message);
				var results=response.message;
				for (var i=0; i < results.length; i++) {
					var newRow = document.createElement("tr");

					var parameterCell = document.createElement("td");
					parameterCell.textContent = results[i].parameter;
					newRow.appendChild(parameterCell);

					var resultCell = document.createElement("td");
					resultCell.textContent = results[i].result;
					newRow.appendChild(resultCell);

					var unitCell = document.createElement("td");
					unitCell.textContent = results[i].unit;
					newRow.appendChild(unitCell);

					tableBody.appendChild(newRow);
				}
			}
		}
	})
}