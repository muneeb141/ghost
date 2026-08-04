import frappe

def create_magic_link_template():
    frappe.init(site="huf-reason.localhost")
    frappe.connect()

    template_name = "Ghost Magic Link"
    if not frappe.db.exists("Email Template", template_name):
        doc = frappe.get_doc({
            "doctype": "Email Template",
            "name": template_name,
            "subject": "Activate Your Account 🚀",
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaec; border-radius: 8px; background-color: #ffffff;">
    <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eaeaec;">
        <h2 style="color: #333333; margin: 0;">Welcome!</h2>
    </div>
    <div style="padding: 20px 0; color: #555555; line-height: 1.6;">
        <p>Hello,</p>
        <p>You requested a magic link to verify your email and securely convert your guest session into a permanent account. We're excited to have you on board!</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{{ magic_link }}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px;">Verify Email &amp; Activate Account</a>
        </p>
        <p style="font-size: 14px; color: #888888; text-align: center;">
            This magic link will safely expire in <strong>{{ expires_in_minutes }} minutes</strong>.
        </p>
        <p style="margin-top: 30px;">If you didn't request this link, you can safely ignore this email.</p>
    </div>
    <div style="text-align: center; padding-top: 20px; border-top: 1px solid #eaeaec; color: #aaaaaa; font-size: 12px;">
        &copy; {{ frappe.utils.get_url() }}
    </div>
</div>"""
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit() # nosemgrep: frappe-manual-commit - required in standalone management CLI script where HTTP transaction wrapping is absent
        print("Template created successfully!")
    else:
        print("Template already exists.")

if __name__ == "__main__":
    create_magic_link_template()
