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
            "fieldtype": "Data"        }
	],
    "onload": (report) => {
        report.page.add_inner_button(__('Download PDF'), function () {
            create_pdf(
                frappe.query_report.get_filter_value("item"),
                frappe.query_report.get_filter_value("parameter"),
                frappe.query_report.get_filter_value("batch_tt")
            );
        })
    }
};

function create_pdf(item, parameter, batch) {
    var w = window.open(
        frappe.urllib.get_full_url("/api/method/tobientrading_custom.tobientrading_custom.report.analysedatenbank.analysedatenbank.download_pdf"  
                + "?item=" + encodeURIComponent(item)
                + "&parameter=" + encodeURIComponent(parameter)
                + "&batch=" + encodeURIComponent(batch))
    );
    if (!w) {
        frappe.msgprint(__("Please enable pop-ups")); return;
    } 
}

