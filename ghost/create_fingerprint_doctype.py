import frappe

def create_doctype():
    if not frappe.db.exists("DocType", "Ghost Fingerprint"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Ghost Fingerprint",
            "module": "Ghost",
            "custom": 0,
            "istable": 0,
            "fields": [
                {
                    "fieldname": "fingerprint",
                    "fieldtype": "Data",
                    "label": "Fingerprint",
                    "unique": 1,
                    "reqd": 1
                },
                {
                    "fieldname": "ghost_email",
                    "fieldtype": "Data",
                    "label": "Ghost Email",
                    "reqd": 1
                },
                {
                    "fieldname": "last_seen",
                    "fieldtype": "Datetime",
                    "label": "Last Seen",
                    "reqd": 1
                }
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print("DocType 'Ghost Fingerprint' created successfully.")
    else:
        print("DocType 'Ghost Fingerprint' already exists.")
