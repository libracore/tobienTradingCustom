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
        listview.page.add_menu_item(__("Import from Excel/XML"), function() {
            import_file();

        });
    }
}

function import_file(){
	var input = document.createElement("input");
	input.type = 'file';
	input.accept = '.xls,.xlsx,.xml';

	input.addEventListener('change', function (event) {
		var file = event.target.files[0];
		if (file) {
			var fileType = file.type;
            if (fileType === "application/xml" || file.name.endsWith('.xml')) {
				read_xml(file);
            } else if (fileType.match('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') || fileType.match('application/vnd.ms-excel') || file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
				read_excel(file);
			} else {
				frappe.msgprint("Invalid file type. Please upload an XML or Excel file.");
			}
		} else {
			frappe.msgprint("No file selected");
		}
	});
	input.click();
}

function read_excel(file){
	var reader = new FileReader();
	reader.addEventListener('load', function (event) {
		var contents = event.target.result;
		extract_data_from_excel(contents);
	});
	reader.onerror = function (event) {
		frappe.msgprint("Error reading file");
	};
	reader.readAsBinaryString(file);
}

function extract_data_from_excel(contents){
	console.log("Extracting data from Excel");
	var workbook = XLSX.read(contents, {type: 'binary'});
	var sheet_name_list = workbook.SheetNames[0];
	var worksheet = workbook.Sheets[sheet_name_list];
	var excelData = XLSX.utils.sheet_to_json(worksheet, {header: 1});
	create_coa_from_excel_data(excelData);
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

function read_xml(file){
	console.log("Reading XML file");
	var reader = new FileReader();
	reader.addEventListener('load', function (event) {
		var contents = event.target.result;
		create_coa_from_xml_data(contents);
	});
	reader.onerror = function (event) {
		frappe.msgprint("Error reading file");
	};
	reader.readAsText(file);
}

function create_coa_from_xml_data(data){
	console.log("Creating COA from XML data");
	console.log(data);
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.create_coa_from_xml_data",
		'args': {
			'data': data
		},
		'callback': function(response){
			if (response.message) {
				frappe.msgprint(response.message);
			}
		}
	})
}