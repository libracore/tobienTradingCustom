// Copyright (c) 2024, libracore AG and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Analysedatenbank"] = {
	"filters": [
		{
            "fieldname":"item",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item"
        },
		{
            "fieldname":"parameter",
            "label": __("Parameter"),
            "fieldtype": "Link",
            "options": "Measurement Parameter"
        },
        {
            "fieldname":"batch_tt",
            "label": __("Batch"),
            "fieldtype": "Link",
            "options": "Batch",        
        },
        {
            "fieldname":"item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group",        
        },
        {
            "fieldname":"test_type",
            "label": __("Test Type"),
            "fieldtype": "Link",
            "options": "Test Type",        
        },
        {
            "fieldname":"subcategory",
            "label": __("Subcategory"),
            "fieldtype": "Data"        
        }
	],
    "onload": (report) => {
        const createPdfButton = (label, options) => {
            report.page.add_inner_button(__(label), function () {
                create_pdf({
                    item: frappe.query_report.get_filter_value("item"),
                    parameter: frappe.query_report.get_filter_value("parameter"),
                    batch: frappe.query_report.get_filter_value("batch_tt"),
                    item_group: frappe.query_report.get_filter_value("item_group"),
                    test_type: frappe.query_report.get_filter_value("test_type"),
                    subcategory: frappe.query_report.get_filter_value("subcategory"),
                    ...options
                });
            });
        };
    
        createPdfButton('Download PDF', { supplier_batch_number: true });
        createPdfButton('PDF without Supplier Batch Number', { supplier_batch_number: false });
    }
};

function create_pdf(options) {
    const {
        item,
        parameter,
        batch,
        item_group,
        test_type,
        subcategory,
        supplier_batch_number
    } = options;

    var w = window.open(
        frappe.urllib.get_full_url("/api/method/tobientrading_custom.tobientrading_custom.report.analysedatenbank.analysedatenbank.download_pdf"  
                + "?item=" + encodeURIComponent(item)
                + "&parameter=" + encodeURIComponent(parameter)
                + "&batch=" + encodeURIComponent(batch))
                + "&item_group=" + encodeURIComponent(item_group)
                + "&test_type=" + encodeURIComponent(test_type)
                + "&subcategory=" + encodeURIComponent(subcategory)
                + "&supplier_batch_number=" + encodeURIComponent(supplier_batch_number)
    );
    if (!w) {
        frappe.msgprint(__("Please enable pop-ups")); return;
    } 
}