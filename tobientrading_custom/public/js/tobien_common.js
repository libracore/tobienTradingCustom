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

    // Fix attachment behavior in email popup:
    // - Uncheck "attach document print" in e-mail window for some doctypes
    // - If there is an attachment by the same name as the document, attach it to emails by default
    const modalObserver = new MutationObserver( () => {

        // A direct child of the <body> tag is being created on a document form
        if(frappe.router.current_route && frappe.router.current_route[0] == 'Form' && cur_frm && cur_frm.doc.name) {

            // Check for attachment with name matching document
            var att_id = null;
            var doc_info = cur_frm.get_docinfo();
            if(doc_info.attachments) {
                doc_info.attachments.every( att => {
                    if(att.file_name.startsWith(cur_frm.doc.name)) {
                        att_id = att.name;
                        return false;
                    }
                    return true;
                });
            }
            if (att_id) {
                // Attach matching file by default
                var selector = 'input[data-file-name="'+att_id+'"]';
                $(selector).prop('checked', true); // Check all matching checkboxes
            }

            // Unattach document print for documents without sensible print formats,
            // as well as for documents with existing PDF attachment
            if(att_id || ['Lead','Opportunity','Customer','Supplier','Contact','Address'].includes(cur_frm.doctype)) {
                $('input[data-fieldname="attach_document_print"]').each(function() {
                    if($(this).prop('checked')) {
                        $(this).click();
                    }
                });
            }

            // Warn when emailing a draft document
            $('.email-draft-warning').remove();
            var email_form_visible = $('input[data-fieldname="send_me_a_copy"]').is(':visible');
            if(email_form_visible && cur_frm.doc.docstatus == 0 && frappe.model.is_submittable(cur_frm.doc.doctype)) {
                $('div.custom-actions').after('<div class="email-draft-warning">Dies ist ein Entwurf - Bitte vor dem Versenden buchen!</div>');
            }

        }
    });

    // Observe direct children of body, which includes creation of the modal window
    modalObserver.observe(document.body, { childList: true });


    // Refresh event on all doctypes
    $(document).on("form-refresh", function (event, frm) {
        frappe.ui.form.on(frm.doctype, {
            refresh: function (frm) {

                // Add shortcut button for email where appropriate
                if(!cur_frm.custom_buttons["&#9993;"]) { //✉
                    cur_frm.add_custom_button(__("&#9993;"), function() {
                        custom_email_dialog();
                    });
                }

                // Modify the "New Email" button at the bottom (timeline)
                $('button:contains("New Email")').off('click');
                $('button:contains("New Email")').on('click', function() {
                    custom_email_dialog();
                });
            }
        });
    });


    document.addEventListener('click',function(event) {

        // Replace email dialog to get a more sensible draft message
        var on_email_menutext = event.target.classList.contains('menu-item-label') && ['E-Mail','Email'].includes(event.target.innerText);
        var on_email_menuitem = event.target.children.length > 0
                                                 && event.target.children[0].classList.contains('menu-item-label')
                                                 && ['E-Mail','Email'].includes(event.target.children[0].innerText);

      if(on_email_menutext || on_email_menuitem) {
          custom_email_dialog();
          event.stopPropagation();
          event.preventDefault();
          $('.menu-item-label:contains("Email")').parent().off('click');
          $('.menu-item-label:contains("E-Mail")').parent().off('click');
        }
    }, true);

    // Catch Ctrl+E
    document.addEventListener('keydown',function(event) {
        if (event.key == 'e' && event.ctrlKey){
            custom_email_dialog();
            event.stopPropagation();
            event.preventDefault();
        }
    }, true);
});


function custom_email_dialog() {
    let lang = (cur_frm.doc.language || 'en').toUpperCase();
    let template_name = cur_frm.doctype + ' ' + lang;
    frappe.db.exists("Email Template", template_name).then(exists => {
        new frappe.erpnextswiss.MailComposer({
            doc: cur_frm.doc,
            frm: cur_frm,
            subject: __(cur_frm.meta.name) + ': ' + cur_frm.docname,
            recipients: cur_frm.doc.email || cur_frm.doc.email_id || cur_frm.doc.contact_email,
            cc: 'order@tobien-trading.com',
            'email_template': exists ? template_name : null,
            attach_document_print: true
        });
        if (cur_frm.doc.doctype == "Sales Invoice" && cur_frm.doc.items[0].sales_order) {
            frappe.call({
                method: "tobientrading_custom.api.delivery_note.get_customer_po",
                args: {
                    so: cur_frm.doc.items[0].sales_order
                },
                callback: function(r) {
                    if(r.message && !r.exc) {
                        set_email_subject("Your PO " + r.message + " (" + cur_frm.doc.name + ")");
                    }
                }
            });
        }
        else if(cur_frm.doc.doctype == "Sales Order" && cur_frm.doc.po_no) {
            set_email_subject("Your PO " + cur_frm.doc.po_no + " (" + cur_frm.doc.name + ")");
        }
        else if(cur_frm.doc.doctype == "Blanket Order") {
            set_email_subject("Your Contract " + cur_frm.doc.your_contract_no + " (" + cur_frm.doc.name + ")");
        }
    });
}

function set_email_subject(subject) {
    setTimeout(() => {
        $('*[data-fieldname="subject"]').val(subject);
    }, 500);
}