frappe.ui.form.on('Item Approval Sensoric', {
    onload: function(frm) {
        if (!frm.doc.sensoric_parameters || frm.doc.sensoric_parameters.length === 0) {

            let default_values = [
                "Color",
                "Odor",
                "Taste",
                "Appearance"
            ];

            default_values.forEach(function(param) {
                let row = frm.add_child("sensoric_parameters");
                row.sensor = param;
            });

            frm.refresh_field("sensoric_parameters");
        }
    }
});