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
	]
};
