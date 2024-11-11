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
            import_from_excel();

        });
    }
}

function import_from_excel(){
	var input = document.createElement("input");
	input.type = 'file';
	input.accept = '.xls,.xlsx';

	// Add an event listener to listen for when a file is selected
	input.addEventListener('change', function (event) {
		var file = event.target.files[0];
		if (file) {
			read_file(file);
		} else {
			frappe.msgprint("No file selected");
		}
	});
	input.click();
}

function read_file(file){
	var reader = new FileReader();
	reader.addEventListener('load', function (event) {
		var contents = event.target.result;
		extract_data(contents);
	});
	reader.onerror = function (event) {
		frappe.msgprint("Error reading file");
	};
	reader.readAsBinaryString(file);
}

function extract_data(contents){
	var workbook = XLSX.read(contents, {type: 'binary'});
	var sheet_name_list = workbook.SheetNames[0];
	var worksheet = workbook.Sheets[sheet_name_list];
	var data = XLSX.utils.sheet_to_json(worksheet, {header: 1});
    console.log(data);
	create_coa_from_excel_data(data);
}

function create_coa_from_excel_data(data){
	frappe.call({
		'method': "tobientrading_custom.tobientrading_custom.doctype.certificate_of_analysis.certificate_of_analysis.create_coa_from_excel_data",
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