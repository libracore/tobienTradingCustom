// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt

load_script("https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.16.9/xlsx.full.min.js", function() { console.log("XLSX loaded"); })

function load_script(url, callback) {
    var script = document.createElement("script");
    script.type = "text/javascript";
    script.src = url;
    script.onload = function() { 
        callback();
    }
    document.getElementsByTagName("head")[0].appendChild(script);
}

frappe.listview_settings['Certificate of Analysis'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__("Import from Excel"), function() {
            import_file("excel");

        });
        listview.page.add_menu_item(__("Import from XML"), function() {
            import_file("xml");

        });
    }
}

function import_file(type){
	var input = document.createElement("input");
	input.type = 'file';
	if (type == "excel") {
		input.accept = '.xls,.xlsx';
	} else if (type == "xml") {
		input.accept = '.xml';
	}

	input.addEventListener('change', function (event) {
		var file = event.target.files[0];
		if (file) {
			read_file(file, type);
		} else {
			frappe.msgprint("No file selected");
		}
	});
	input.click();
}

function read_file(file, type){
	var reader = new FileReader();
	reader.addEventListener('load', function (event) {
		var contents = event.target.result;
		if (type == "excel") {
			extract_data_from_excel(contents);
		} else if (type == "xml") {
			extract_data_from_xml(contents);
		}
	});
	reader.onerror = function (event) {
		frappe.msgprint("Error reading file");
	};
	if (type == "excel") {
		reader.readAsBinaryString(file);
	} else if (type == "xml") {
		reader.readAsText(file);
	}
}

function extract_data_from_xml(contents){
	var parser = new DOMParser();
	var xmlDoc = parser.parseFromString(contents, "application/xml");
	create_coa_from_xml_data(xmlDoc);
}

function extract_data_from_excel(contents){
	var workbook = XLSX.read(contents, {type: 'binary'});
	var sheet_name_list = workbook.SheetNames[0];
	var worksheet = workbook.Sheets[sheet_name_list];
	var excelData = XLSX.utils.sheet_to_json(worksheet, {header: 1});
	create_coa_from_excel_data(excelData);
}

function create_coa_from_xml_data(data){
	var xmlString = (new XMLSerializer()).serializeToString(data);
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.create_coa_from_xml_data",
		'args': {
			'data': xmlString
		},
		'callback': function(response){
			if (response.message) {
				frappe.msgprint(response.message);
			}
		}
	})
}

function create_coa_from_excel_data(data){
	const jsonData = JSON.stringify(data);
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.create_coa_from_excel_data",
		'args': {
			'data': jsonData
		},
		'callback': function(response){
			if (response.message) {
				frappe.msgprint(response.message);
			}
		}
	})
}