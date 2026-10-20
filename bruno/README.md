# Manual API checks

Open this folder in Bruno and select the Local environment. Set `baseUrl` to your
site, `target_email` to a mailbox you control, and `otp_code` to the actual delivered
code. The `.invalid` default deliberately cannot deliver. No production credentials
belong in the collection. Configure the OAuth Client, email template/account and
OTP/signup policy in Ghost Settings first.

## Direct login

1. Direct Auth / Send OTP requests **Login**, not Conversion.
2. Set `otp_code` from the message, then run Direct Auth / Login.
3. Default success establishes a native cookie session. It does not include tokens.
   Add the configured `client_id` explicitly if testing a headless token consumer.
4. Reusing the same code must fail. Do not call validate_otp before login.

## Anonymous conversion

1. Create Ghost Session saves the server identity and bearer credentials as variables.
2. Send OTP (Conversion) sends a code to `target_email`.
3. Set `otp_code` and use Convert (Secure), authenticated as that Ghost.
4. Reject Unverified Conversion is a **negative** test: it must return HTTP 403.
5. The fingerprint request creates a new identity; it never resumes an old one.
6. Google uses a real provider ID token and the originating Ghost bearer. Magic links
   also require the originating bearer plus the token from the delivered email.

Refresh Token rotates credentials once; save its replacement response before another
call. Analytics calls require the enabled feature and an authorized manager account.

This is a manual collection, not a claim of automated Bruno CLI execution. Automated
coverage uses the real Frappe suite, HTTP smoke script and compatibility workflow.
See [upgrade impacts](../docs/API_MIGRATION.md) and [evidence](../docs/COMPATIBILITY_REPORT.md).
