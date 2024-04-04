/* Copyright (C) libracore, 2024
 * https://www.libracore.com or https://git.libracore.io/libracore
 */

const NAMING_SERIES = {
    'Tobien Trading GmbH': {
        'Sales Invoice': "SI-CH-.YY.####",
        'Credit Note': "CN-CH-.YY.####",
        'Delivery Note': "DN-CH-.YY.####",
        'Sales Order': "SO-CH-.YY.####",
        'Quotation': "QN-CH-.YY.####",
        'Payment Reminder': "DG-CH-.YY.####",
        'Material Request': "MR-CH-.YY.####",
        'Request for Quotation': "RQ-CH-.YY.####",
        'Supplier Quotation': "SQ-CH-.YY.####",
        'Purchase Order': "PO-CH-.YY.####",
        'Purchase Receipt': "PR-CH-.YY.####",
        'Purchase Invoice': "PI-CH-.YY.####"
    },
    'Tobien Trading Deutschland GmbH': {
        'Sales Invoice': "SI-DE-.YY.####",
        'Credit Note': "CN-DE-.YY.####",
        'Delivery Note': "DN-DE-.YY.####",
        'Sales Order': "SO-DE-.YY.####",
        'Quotation': "QN-DE-.YY.####",
        'Payment Reminder': "DG-DE-.YY.####",
        'Material Request': "MR-DE-.YY.####",
        'Request for Quotation': "RQ-DE-.YY.####",
        'Supplier Quotation': "SQ-DE-.YY.####",
        'Purchase Order': "PO-DE-.YY.####",
        'Purchase Receipt': "PR-DE-.YY.####",
        'Purchase Invoice': "PI-DE-.YY.####"
    }
}

function prepare_naming_series(frm) {
    if (frm.doc.__islocal) {
        if ((frm.doc.doctype === "Sales Invoice") && (frm.doc.is_return === 1)) {
            cur_frm.set_value("naming_series", NAMING_SERIES[frm.doc.company]['Credit Note']);
        } else {
            cur_frm.set_value("naming_series", NAMING_SERIES[frm.doc.company][frm.doc.doctype]);
        }
    }
}
