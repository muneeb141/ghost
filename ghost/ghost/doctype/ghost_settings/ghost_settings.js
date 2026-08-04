frappe.ui.form.on('Ghost Settings', {
	refresh: function(frm) {
		frm.trigger('lead_doctype');
	},
	lead_doctype: function(frm) {
		if (frm.doc.lead_doctype) {
			frappe.model.with_doctype(frm.doc.lead_doctype, function() {
				var fields = frappe.meta.get_docfields(frm.doc.lead_doctype);
				var options = fields
					.filter(df => !['Section Break', 'Column Break', 'Tab Break', 'HTML'].includes(df.fieldtype))
					.map(df => ({
						label: `${df.label} (${df.fieldname})`,
						value: df.fieldname
					}));

				// Also add 'owner' as it's a standard field not always explicitly in get_docfields
				options.push({label: 'Owner (owner)', value: 'owner'});
				options.push({label: 'Name (name)', value: 'name'});
				
				// Sort alphabetically by label
				options.sort((a, b) => a.label.localeCompare(b.label));
				
				// Add a blank option at the top
				options.unshift('');

				frm.set_df_property('lead_email_fieldname', 'options', options);
				frm.set_df_property('lead_ghost_fieldname', 'options', options);
				frm.set_df_property('lead_status_fieldname', 'options', options);
			});
		} else {
			frm.set_df_property('lead_email_fieldname', 'options', []);
			frm.set_df_property('lead_ghost_fieldname', 'options', []);
			frm.set_df_property('lead_status_fieldname', 'options', []);
		}
	}
});
