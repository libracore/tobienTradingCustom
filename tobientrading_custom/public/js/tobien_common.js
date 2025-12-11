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

$(document).ready(function() {

    document.addEventListener('click',function(event) {

        // Replace email dialog to get a more sensible draft message
        var on_email_menutext = event.target.classList.contains('menu-item-label') && ['E-Mail','Email'].includes(event.target.innerText);
        var on_email_menuitem = event.target.children.length > 0
                                                 && event.target.children[0].classList.contains('menu-item-label')
                                                 && ['E-Mail','Email'].includes(event.target.children[0].innerText);

      if(on_email_menutext || on_email_menuitem) {
          custom_email_dialog(event);
          event.stopPropagation();
          event.preventDefault();
          $('.menu-item-label:contains("Email")').parent().off('click');
          $('.menu-item-label:contains("E-Mail")').parent().off('click');
        }
    }, true);

    // Catch Ctrl+E
    document.addEventListener('keydown',function(event) {
        if (event.key == 'e' && event.ctrlKey){
            custom_email_dialog(event);
            event.stopPropagation();
            event.preventDefault();
        }
    }, true);
});


function custom_email_dialog(e) {
    let lang = cur_frm.doc.language.toUpperCase() || 'EN';
    new frappe.erpnextswiss.MailComposer({
        doc: cur_frm.doc,
        frm: cur_frm,
        subject: __(cur_frm.meta.name) + ': ' + cur_frm.docname,
        recipients: cur_frm.doc.email || cur_frm.doc.email_id || cur_frm.doc.contact_email,
        cc: 'order@tobien-trading.com',
        'email_template': cur_frm.doctype + ' ' + lang,
        attach_document_print: true
    });
}