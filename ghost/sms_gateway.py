# Copyright (c) 2025, OTP Generation and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def send(otp_code=None, phone=None, **kwargs):
	"""SMS sender for Ghost OTP delivery via the android-sms-gateway device.

	Wired up through Ghost Settings.sms_sender ("ghost.sms_gateway.send") and
	invoked by ghost.sender.send_otp_sms. Credentials are read from site config
	(never hardcoded); set them with:
	    bench set-config -g sms_gateway_login <login>
	    bench set-config -g sms_gateway_password <password>

	Args:
	    otp_code: The OTP code to deliver.
	    phone: Destination phone number.
	    **kwargs: Extra context from the sender (e.g. otp_name); ignored here.

	Returns:
	    The gateway message id for the queued SMS.
	"""
	# Lazy import so the app loads even if the gateway package is absent.
	from android_sms_gateway import client, domain

	login = frappe.conf.get("sms_gateway_login")
	password = frappe.conf.get("sms_gateway_password")

	if not login or not password:
		frappe.log_error(
			message="sms_gateway_login/sms_gateway_password missing from site config",
			title="OTP Sender",
		)
		raise frappe.ValidationError(_("SMS gateway credentials are not configured"))

	# Optional SIM slot selection (1-based). None = device default.
	sim_number = kwargs.get("sim_number")

	message = domain.Message(
		phone_numbers=[phone],
		text_message=domain.TextMessage(
			text=f"Your OTP is {otp_code}. Do not share it with anyone."
		),
		with_delivery_report=True,
		sim_number=int(sim_number) if sim_number else None,
	)

	with client.APIClient(login, password) as c:
		state = c.send(message)
		return state.id
