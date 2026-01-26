frappe.ui.form.on('Transport Order', {

    setup: function(frm) {
        frm.set_query("purchase_order", function() {
            return {
                filters: [
                    ["Purchase Order","status", "in", ["Draft", "To Receive and Bill", "To Bill"]]
                ]
            };
        });
        frm.set_query("sales_order", function() {
            return {
                filters: [
                    ["Sales Order","status", "in", ["Draft", "To Deliver and Bill", "To Bill"]]
                ]
            };
        });
    },
    loading_address: function(frm) {
        if (frm.doc.loading_address) {
            fetch_loading_address_details(frm);
        }
    },
    company_shipping_address: function(frm) {
        if (frm.doc.company_shipping_address) {
            fetch_shipping_address_details(frm);
        }
    },
    contact_person: function(frm){
        if ( frm.doc.contact_person ) {
            fetch_contact_person_details(frm);
        }
    },
    company_contact_person: function(frm){
        if ( frm.doc.company_contact_person) {
            fetch_company_contact_person_details(frm);
        }
    }
});


function fetch_company_contact_person_details(frm){
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Contact",
            "name": frm.doc.company_contact_person
        },
        "async": false,
        "callback": function(response) {
            var contact = response.message;
            var name = ( contact.salutation || "" )  + " " + contact.first_name + " " + contact.last_name;
            var phone = ( contact.phone || contact.mobile_no );
            cur_frm.set_value("company_contact", name || "");
            cur_frm.set_value("company_phone", phone || "");
            cur_frm.set_value("company_email", contact.email_id || "");
        }
    });
}


function fetch_contact_person_details(frm){
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Contact",
            "name": frm.doc.contact_person
        },
        "async": false,
        "callback": function(response) {
            var contact = response.message;
            var name = ( contact.salutation || "" )  + " " + contact.first_name + " " + contact.last_name;
            var phone = ( contact.phone || contact.mobile_no );
            cur_frm.set_value("contact", name || "");
            cur_frm.set_value("phone", phone || "");
            cur_frm.set_value("email", contact.email_id || "");
        }
    });
}


function fetch_loading_address_details(frm) {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Address",
            "name": frm.doc.loading_address
        },
        "async": false,
        "callback": function(response) {
            var address = response.message;
            var details = "<b>" + address.address_title + "</b><br>" + address.address_line1 + "<br>" + address.pincode + " " + address.city + "<br>" + address.country;
            cur_frm.set_value("loading_address_details", details);
        }
    });
}


function fetch_shipping_address_details(frm) {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
            "doctype": "Address",
            "name": frm.doc.company_shipping_address
        },
        "async": false,
        "callback": function(response) {
            var address = response.message;
            var details = "<b>" + address.address_title + "</b><br>" + address.address_line1 + "<br>" + address.pincode + " " + address.city + "<br>" + address.country;
            cur_frm.set_value("shipping_address_details", details);
        }
    });
}
