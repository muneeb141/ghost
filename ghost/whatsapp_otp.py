# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.integrations.utils import make_post_request


def send(otp_code=None, phone=None, **kwargs):
	"""Send OTP over WhatsApp using the approved authentication template.

	Wired through Ghost Settings.sms_sender ("ghost.whatsapp_otp.send") and
	invoked by ghost.sender.send_otp_sms. The copy-code auth template is sent
	directly via the WhatsApp Cloud API — frappe_whatsapp's send_template can't
	emit the OTP button parameter. Credentials are read from the default
	outgoing WhatsApp Account (token stored encrypted there); nothing hardcoded.

	The approved template name/language live in site config so the same code
	works across servers with different templates:
	    bench set-config -g ghost_otp_whatsapp_template <template_name>
	    bench set-config -g ghost_otp_whatsapp_template_lang <lang_code>  # optional, defaults en_US

	Args:
	    otp_code: The OTP code to deliver.
	    phone: Destination phone number (with or without leading +).
	    **kwargs: Extra context from the sender (e.g. otp_name); ignored here.

	Returns:
	    The WhatsApp message id (wamid) for the sent OTP.
	"""
	# Fail fast if this server has no OTP template configured.
	template_name = frappe.conf.get("ghost_otp_whatsapp_template")
	if not template_name:
		frappe.throw(_("ghost_otp_whatsapp_template is not set in site config"))
	template_lang = frappe.conf.get("ghost_otp_whatsapp_template_lang") or "en_US"

	account_name = frappe.db.get_value(
		"WhatsApp Account", {"is_default_outgoing": 1, "status": "Active"}, "name"
	)
	if not account_name:
		frappe.log_error(
			message="No active default-outgoing WhatsApp Account configured",
			title="OTP Sender",
		)
		raise frappe.ValidationError(_("No WhatsApp account configured for OTP"))

	account = frappe.get_doc("WhatsApp Account", account_name)
	code = str(otp_code)
	to = "".join(ch for ch in str(phone) if ch.isdigit())

	data = {
		"messaging_product": "whatsapp",
		"to": to,
		"type": "template",
		"template": {
			"name": template_name,
			"language": {"code": template_lang},
			"components": [
				{"type": "body", "parameters": [{"type": "text", "text": code}]},
				{
					"type": "button",
					"sub_type": "url",
					"index": "0",
					"parameters": [{"type": "text", "text": code}],
				},
			],
		},
	}
	headers = {
		"authorization": f"Bearer {account.get_password('token')}",
		"content-type": "application/json",
	}

	try:
		response = make_post_request(
			f"{account.url}/{account.version}/{account.phone_id}/messages",
			headers=headers,
			data=json.dumps(data),
		)
		return response["messages"][0]["id"]
	except Exception:
		frappe.log_error(
			message=f"Error sending OTP WhatsApp: {frappe.get_traceback()}", title="OTP Sender"
		)
		raise
