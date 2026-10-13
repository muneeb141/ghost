# User details API

Both endpoints use the current Frappe session or bearer token. Neither accepts a user ID.

## Read profile

`GET /api/method/ghost.api.user_details.get_user_details`

Returns `name`, `email`, `mobile_no`, `first_name`, `last_name`, `full_name`, and `user_image` for the signed-in user.

## Update mobile number

1. Request a phone OTP through `POST /api/method/ghost.api.otp.send_otp` with `phone=<new number>` and `purpose=Conversion`.
2. Call `POST /api/method/ghost.api.user_details.update_mobile_number` with `mobile_no=<new number>` and `otp_code=<received code>`.

The endpoint rejects guests, missing fields, numbers already assigned to another user, and invalid or expired OTPs. It updates the signed-in user's record only after the OTP is verified. Normal Frappe request transaction handling commits the change.
