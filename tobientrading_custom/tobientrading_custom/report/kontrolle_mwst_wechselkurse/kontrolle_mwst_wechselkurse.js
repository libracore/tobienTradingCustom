// Copyright (c) 2016-2026, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kontrolle MwSt Wechselkurse"] = {
    "filters": [
        {
            "fieldname":"quarter",
            "label": __("Quarter"),
            "fieldtype": "Select",
            "options": [],
            "reqd": 1
        },
        {
            "fieldname":"code",
            "label": __("Code"),
            "fieldtype": "Select",
            "options": "302\n303\n312\n313\n382\n383\n400\n405",
            "default" : "200",
            "reqd": 1
        },
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default" : frappe.defaults.get_default("Company"),
            "reqd": 1
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        // the total row is part of the data (see get_total_row), highlight it
        if (data && data.is_total_row) {
            value = "<b>" + value + "</b>";
        }
        return value;
    },
    "onload": function(report) {
        // fill the quarter options from the fiscal years
        frappe.call({
            "method": "tobientrading_custom.tobientrading_custom.report.kontrolle_mwst_wechselkurse.kontrolle_mwst_wechselkurse.get_quarter_options",
            "callback": function(r) {
                if (!r.message) {
                    return;
                }
                var quarter_filter = report.get_filter("quarter");
                quarter_filter.df.options = r.message.options;
                quarter_filter.refresh();
                if (!quarter_filter.get_value() && r.message.default) {
                    quarter_filter.set_value(r.message.default);
                }
            }
        });
    }
};
