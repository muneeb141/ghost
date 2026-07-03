# OTP Delivery Setup (WhatsApp / SMS)

Ghost delivers OTPs through a pluggable sender. `Ghost Settings.sms_sender` holds a
dotted path to a Python function `send(otp_code, phone, **kwargs)` that is loaded
dynamically (`frappe.get_attr`) and called for the SMS/phone delivery branch.

Two senders ship with the app:

| Channel | `sms_sender` value | File |
|---|---|---|
| WhatsApp (Cloud API auth template) | `ghost.whatsapp_otp.send` | `ghost/whatsapp_otp.py` |
| SMS (android-sms-gateway device)   | `ghost.sms_gateway.send`  | `ghost/sms_gateway.py` |

Pick one, set `sms_sender` to it, and configure that channel below. Switching
channels later is just changing `sms_sender` — no code change.

---

## Option A — WhatsApp OTP

**Prerequisites (per Meta WhatsApp Business Account, once):**
- The number must be **registered on the Cloud API** (able to send). A number that
  only *reads* returns `#133010 Account not registered` on send.
- An **APPROVED AUTHENTICATION** template with a **copy-code** OTP button must exist
  on that WABA (e.g. `otp_verification`). OTP content is rejected in UTILITY/MARKETING
  (`INCORRECT_CATEGORY`) — it must be the AUTHENTICATION category.

**Per site:**
1. Install `frappe_whatsapp` alongside `ghost` (the sender reads its `WhatsApp Account` doctype).
2. Create a **WhatsApp Account** with the WABA creds (token, url, version, phone_id,
   business_id, app_id), `status = Active`, `is_default_outgoing = 1`.
3. Put the template name/language in **common_site_config.json** (not hardcoded, so the
   same code works on any server):
   ```bash
   bench set-config -g ghost_otp_whatsapp_template otp_verification
   bench set-config -g ghost_otp_whatsapp_template_lang en_US   # optional, defaults en_US
   ```
   If `ghost_otp_whatsapp_template` is unset, `send()` fails fast with a clear error.
4. **Ghost Settings** → `sms_sender = ghost.whatsapp_otp.send`,
   `otp_delivery_type` = SMS / Both / Phone Lookup, `sandbox_mode` = off.
5. `bench restart`.

The OTP code is sent as both the template body `{{1}}` and the copy-code button param
(the format Meta requires). Template resolution happens on Meta's servers by name —
no local `WhatsApp Templates` record is needed.

---

## Option B — SMS OTP (android-sms-gateway)

1. `./env/bin/pip install android-sms-gateway`
2. Store gateway creds in site config (never in the repo):
   ```bash
   bench set-config -g sms_gateway_login <login>
   bench set-config -g sms_gateway_password <password>
   ```
3. **Ghost Settings** → `sms_sender = ghost.sms_gateway.send`,
   `otp_delivery_type` = SMS / Both / Phone Lookup, `sandbox_mode` = off.
4. `bench restart`.

Optional: pass `sim_number` in the SIM slot via kwargs if the device is multi-SIM.

---

## Test end-to-end

```bash
curl -X POST http://your-site:8000/api/method/ghost.api.otp.send_otp \
  -d 'phone=+9199XXXXXXXX' -d 'purpose=Conversion'
```
A `200` means the OTP was **generated** — delivery happens on the sender side. If the
message doesn't arrive, check the **Error Log** entries titled `OTP Sender`.

## Fail-safe behavior

Sending never breaks OTP generation or the API:
- `sms_sender` blank → send is skipped silently (OTP still generated/stored).
- `sms_sender` set but its config/template missing → sender raises; caught and logged
  as "OTP generated but failed to send"; API still returns 200.
- Note: `sandbox_mode` on short-circuits everything and returns the fixed sandbox code
  with **no** real send — turn it off for live delivery.
