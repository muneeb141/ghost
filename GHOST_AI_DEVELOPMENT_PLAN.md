# Ghost App — AI Development Implementation Plan

> This document is a playbook for building each feature on the Ghost roadmap using AI-assisted development. Each feature section contains the **what**, **why**, **where** (exact files), **how** (step-by-step), and **AI prompt templates** so you can hand each task to an AI agent and get consistent, production-quality results.

---

## Current Status

> [!IMPORTANT]
> **Last Updated:** 2026-08-02 | **Updated By:** AI Consultant
> 
> This section must be updated every time a feature's status changes. Use the statuses below:
> - 🔴 `Not Started` — No work has begun
> - 🟡 `In Progress` — Actively being developed
> - 🟢 `Completed` — Developed, tested, and merged
> - 🔵 `In Review` — Code written, awaiting review/PR merge
> - ⚪ `Deferred` — Postponed to a later date

| # | Feature | Phase | Status | Branch | Notes |
|---|---------|-------|--------|--------|-------|
| 1 | Conversion Analytics Dashboard | Phase 1 | 🟢 Completed | `feat/conversion-analytics-dashboard` | — |
| 2 | Event Webhooks | Phase 1 | 🟢 Completed | `feat/event-webhooks` | — |
| 3 | Magic Link Conversions | Phase 1 | 🟢 Completed | `feat/magic-link` | — |
| 4 | Social Login (Google) | Phase 2 | 🟢 Completed | `feat/social-login` | — |
| 5 | Soft Lead Capture | Phase 2 | 🟢 Completed | `feat/soft-lead-capture` | — |
| 6 | Multi-Device Ghost Merging | Phase 2 | 🟢 Completed | `feat/multi-device-merge` | — |
| 7 | Conversion Funnel API | Phase 3 | 🔴 Not Started | `feat/conversion-funnel-api` | — |
| 8 | Bulk Ghost Cleanup | Phase 3 | 🔴 Not Started | `feat/bulk-ghost-cleanup` | — |
| 9 | Ghost Session Fingerprinting | Phase 3 | 🔴 Not Started | `feat/session-fingerprinting` | — |

**Completed:** 6/9 &nbsp;|&nbsp; **In Progress:** 0/9

### Recently Completed
- Feature 6: Multi-Device Ghost Merging
- Feature 5: Soft Lead Capture
- Feature 4: Social Login (Google)
- Feature 3: Magic Link Conversions
- Feature 2: Event Webhooks

### Changelog
| Date | Feature | Change | By |
|------|---------|--------|----|
| 2026-08-02 | Feature 6 | Developed multi-device ghost merging based on capture email | AI Consultant |
| 2026-08-02 | Feature 5 | Developed Soft Lead Capture and scheduled reminders | AI Consultant |
| 2026-08-02 | Feature 4 | Developed Google Sign-In conversion | AI Consultant |
| 2026-08-02 | Feature 3 | Developed Magic Link conversions via email | AI Consultant |
| 2026-08-02 | Feature 2 | Developed event webhooks and realtime events | AI Consultant |
| 2026-08-02 | Feature 1 | Developed conversion analytics dashboard | AI Consultant |
| 2026-08-02 | — | Initial plan created with all 9 features | AI Consultant |
| 2026-08-02 | Core App | Applied performance & idempotency patches from upstream (`perf/ghost-conversion-improvements`) | AI Consultant |
| 2026-08-02 | Conversion Analytics Dashboard | Added conversion logging (settings toggles + `Ghost Conversion Log` doctype), `ghost-analytics` desk page, and daily retention cleanup task | AI Consultant |


## Mandatory Rule: All Features Must Be Configurable

> [!CAUTION]
> **Every feature in this document MUST be behind a toggle in Ghost Settings.** No feature should be hardcoded to "always on". Administrators must be able to enable/disable each feature independently from the Ghost Settings DocType. This is non-negotiable.

**Pattern for every new feature:**
1. Add a `Check` field to `Ghost Settings` (e.g., `enable_webhooks`, `enable_magic_link`)
2. Default the field to `0` (disabled)
3. Guard the feature logic with `if not settings.enable_<feature>: return`
4. Group related fields under a dedicated `Section Break` or `Tab Break` in Ghost Settings
5. Use `depends_on` to show/hide related config fields based on the toggle

---

## Ground Rules for AI Development

> [!IMPORTANT]
> Every AI session working on this app **must** read `AGENTS.md` before writing any code. It contains the consultant role, architecture context, and hard rules that prevent regressions.

### Before Starting Any Feature
1. **Read** `AGENTS.md` for role rules and architecture context
2. **Check** `ghost/ghost/doctype/ghost_settings/ghost_settings.json` to see if a settings toggle already exists
3. **Check** `ghost/api/` to see if a partial implementation exists
4. **Branch** from `develop` with a descriptive name: `feat/feature-name`
5. **Test** with `bench --site huf-reason.localhost run-tests --app ghost`
6. **Commit** with conventional commit messages

### After Completing Any Feature
1. Add/update unit tests in `ghost/tests/`
2. Update Bruno collection in `bruno/`
3. Update `README.md` if user-facing
4. Update `AGENTS.md` architecture section if it changes the app's core design
5. Create detailed commit messages and push to a feature branch

---

## Phase 1 — High Impact, Core Improvements

---

### Feature 1: Conversion Analytics Dashboard

**Goal:** Give administrators visibility into ghost user behavior — how many are created, how many convert, how long it takes, and where users drop off.

**Ghost Settings Fields Required:**
- `enable_conversion_logging` (Check, default 0) — Toggle conversion event logging
- `conversion_log_retention_days` (Int, default 90) — Auto-delete old logs after N days

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/ghost/doctype/ghost_conversion_log/ghost_conversion_log.json` | DocType to log every conversion event |
| NEW | `ghost/ghost/doctype/ghost_conversion_log/ghost_conversion_log.py` | Controller (minimal) |
| NEW | `ghost/ghost/page/ghost_analytics/ghost_analytics.js` | Frontend dashboard page |
| NEW | `ghost/ghost/page/ghost_analytics/ghost_analytics.html` | Page template |
| NEW | `ghost/ghost/page/ghost_analytics/ghost_analytics.py` | Backend API for analytics data |
| NEW | `ghost/ghost/page/ghost_analytics/ghost_analytics.json` | Page definition |
| MODIFY | `ghost/api/ghost.py` | Log conversion events after success (guarded by `enable_conversion_logging`) |
| MODIFY | `ghost/hooks.py` | Register the new page module |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add `enable_conversion_logging` and `conversion_log_retention_days` |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - `enable_conversion_logging` (Check, default 0)
   - `conversion_log_retention_days` (Int, default 90)
   - Group under a new "Analytics" Tab Break

2. **Create `Ghost Conversion Log` DocType** with fields:
   - `ghost_email` (Data) — The ghost user's email
   - `real_email` (Data) — The converted real email
   - `conversion_mode` (Select: rename / manual_migration / already_converted)
   - `conversion_duration_ms` (Float) — Total time in milliseconds
   - `converted_at` (Datetime) — When conversion happened
   - `client_info` (Small Text) — User-Agent / device info (optional)

3. **Log conversions in `convert_to_real_user`:**
   ```python
   if settings.enable_conversion_logging:
       frappe.get_doc({
           "doctype": "Ghost Conversion Log",
           "ghost_email": ghost_email,
           "real_email": real_email,
           ...
       }).insert(ignore_permissions=True)
   ```

4. **Create the analytics page** with these metrics:
   - Total Ghost Sessions (count of users matching `ghost_*@{domain}`)
   - Total Conversions (count of `Ghost Conversion Log`)
   - Conversion Rate (conversions / sessions × 100)
   - Average Time to Convert (avg of `conversion_duration_ms`)
   - Daily/Weekly/Monthly trend charts
   - Drop-off rate (sessions - conversions that expired without converting)

5. **Add scheduled cleanup** to delete logs older than `conversion_log_retention_days`.

6. **Add tests** to verify conversion log creation and that it respects the toggle.

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_conversion_logging (Check, default 0) and 
   conversion_log_retention_days (Int, default 90) to Ghost Settings under 
   a new "Analytics" Tab Break.
2. Create a "Ghost Conversion Log" DocType in the ghost module with fields: 
   ghost_email, real_email, conversion_mode, conversion_duration_ms, 
   converted_at.
3. Modify convert_to_real_user in ghost/api/ghost.py to insert a log entry 
   after every successful conversion — ONLY if settings.enable_conversion_logging 
   is enabled.
4. Create a Frappe Page called "Ghost Analytics" that queries the log and 
   displays: total sessions, total conversions, conversion rate %, and 
   average conversion time.
5. Add a scheduled task to delete logs older than conversion_log_retention_days.
6. Add unit tests that verify logging works when enabled and is skipped when disabled.
```

---

### Feature 2: Event Webhooks

**Goal:** Allow external systems (CRM, Klaviyo, Zapier) to react when a ghost user converts by firing a webhook or Frappe hook.

**Ghost Settings Fields Required:**
- `enable_webhooks` (Check, default 0) — Master toggle for webhook system
- `webhook_url` (Data, depends_on enable_webhooks) — URL to POST conversion events to
- `webhook_secret` (Password, depends_on enable_webhooks) — HMAC secret for signature verification
- `enable_realtime_events` (Check, default 0, depends_on enable_webhooks) — Toggle Frappe realtime events

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/events.py` | Centralized event dispatcher |
| MODIFY | `ghost/api/ghost.py` | Fire events after conversion (guarded by `enable_webhooks`) |
| MODIFY | `ghost/hooks.py` | Expose `ghost_conversion_hooks` |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add webhook fields under new section |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - New Section Break: "Webhooks & Events"
   - `enable_webhooks` (Check, default 0)
   - `webhook_url` (Data, depends_on `enable_webhooks`)
   - `webhook_secret` (Password, depends_on `enable_webhooks`)
   - `enable_realtime_events` (Check, default 0, depends_on `enable_webhooks`)

2. **Create `ghost/events.py`** with:
   ```python
   def on_ghost_converted(ghost_email, real_email, conversion_mode, tokens=None):
       """Fire all registered hooks when a ghost converts."""
       settings = frappe.get_single("Ghost Settings")
       if not settings.enable_webhooks:
           return
       
       # 1. Fire webhook if URL configured
       if settings.webhook_url:
           enqueue_webhook(settings.webhook_url, settings.webhook_secret, payload)
       
       # 2. Publish realtime event if enabled
       if settings.enable_realtime_events:
           frappe.publish_realtime("ghost_converted", {"user": real_email})
       
       # 3. Fire Frappe hooks for other apps
       for handler in frappe.get_hooks("ghost_conversion_hooks"):
           frappe.call(handler, ghost_email=ghost_email, real_email=real_email)
   ```

3. **Call from `convert_to_real_user`** after the response is built:
   ```python
   if settings.enable_webhooks:
       from ghost.events import on_ghost_converted
       on_ghost_converted(ghost_email, real_email, conversion_mode, new_tokens)
   ```

4. **Expose in `hooks.py`** so other Frappe apps can listen:
   ```python
   ghost_conversion_hooks = []  # Other apps can append their handlers
   ```

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_webhooks (Check, default 0), webhook_url (Data), 
   webhook_secret (Password), and enable_realtime_events (Check, default 0) 
   to Ghost Settings under a new "Webhooks & Events" Section Break. Use 
   depends_on for webhook_url, webhook_secret, and enable_realtime_events 
   so they only show when enable_webhooks is checked.
2. Create ghost/events.py with on_ghost_converted that: sends a POST webhook 
   with HMAC signature (if webhook_url configured), publishes a Frappe 
   realtime event (if enable_realtime_events), and calls any functions 
   registered in hooks.py under ghost_conversion_hooks.
3. ALL event logic must be guarded by: if not settings.enable_webhooks: return
4. Call on_ghost_converted from convert_to_real_user after success.
5. Add tests that verify: (a) nothing fires when toggle is off, (b) webhook 
   fires when toggle is on.
```

---

### Feature 3: Magic Link Conversions

**Goal:** Instead of a 6-digit OTP code, send the user an email with a clickable link that automatically completes the conversion.

**Ghost Settings Fields Required:**
- `enable_magic_link` (Check, default 0) — Toggle magic link support
- `magic_link_expiry_minutes` (Int, default 30, depends_on enable_magic_link) — Link expiry
- `magic_link_redirect_url` (Data, depends_on enable_magic_link) — Where to redirect after success
- `magic_link_email_template` (Link to Email Template, depends_on enable_magic_link) — Email template for magic link emails

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/api/magic_link.py` | Generate and verify magic links |
| NEW | `ghost/www/convert.py` | Web handler for magic link clicks |
| NEW | `ghost/www/convert.html` | Success/error page template |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add magic link fields |
| MODIFY | `ghost/ghost/doctype/otp/otp.json` | Add `magic_link_token` field (or create separate doctype) |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - New Section Break: "Magic Link" (under Conversion Settings or new Tab)
   - `enable_magic_link` (Check, default 0)
   - `magic_link_expiry_minutes` (Int, default 30, depends_on `enable_magic_link`)
   - `magic_link_redirect_url` (Data, depends_on `enable_magic_link`)
   - `magic_link_email_template` (Link to Email Template, depends_on `enable_magic_link`)

2. **Create `ghost/api/magic_link.py`:**
   ```python
   @frappe.whitelist(allow_guest=True)
   def send_magic_link(ghost_email, real_email):
       settings = frappe.get_single("Ghost Settings")
       if not settings.enable_magic_link:
           frappe.throw(_("Magic Link feature is not enabled"))
       # Generate secure token, store, send email with link
   ```

3. **Web handler (`ghost/www/convert.py`):**
   - Validate token exists, not expired, not used
   - Extract ghost_email and real_email
   - Call `convert_to_real_user` internally (bypassing OTP since magic link IS the verification)
   - Redirect to `magic_link_redirect_url` or show success page

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_magic_link (Check, default 0), magic_link_expiry_minutes 
   (Int, default 30), magic_link_redirect_url (Data), and 
   magic_link_email_template (Link to Email Template) to Ghost Settings. 
   All dependent fields must use depends_on eval:doc.enable_magic_link==1.
2. Create ghost/api/magic_link.py with send_magic_link(ghost_email, real_email) 
   that: checks settings.enable_magic_link first, generates a secure token, 
   stores it, builds a URL, and sends an email.
3. Create ghost/www/convert.py as the web endpoint that validates the token 
   and calls convert_to_real_user.
4. Add tests that verify: (a) magic link fails when toggle is off, (b) works 
   when enabled, (c) expired links are rejected.
```

---

## Phase 2 — Growth & Engagement

---

### Feature 4: Social Login Conversion (Google Sign-In)

**Goal:** Let ghost users click "Continue with Google" to convert instantly without OTP.

**Ghost Settings Fields Required:**
- `enable_social_login` (Check, default 0) — Toggle social login conversions
- `google_client_id` (Data, depends_on enable_social_login) — Google OAuth Client ID for token verification

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/api/social.py` | Google/Apple token verification |
| MODIFY | `ghost/api/ghost.py` | New conversion path that skips OTP |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add social login fields |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - New Section Break: "Social Login" (under Conversion Settings tab)
   - `enable_social_login` (Check, default 0)
   - `google_client_id` (Data, depends_on `enable_social_login`)

2. **Create `ghost/api/social.py`:**
   ```python
   @frappe.whitelist()
   def convert_with_google(ghost_email, id_token):
       settings = frappe.get_single("Ghost Settings")
       if not settings.enable_social_login:
           frappe.throw(_("Social Login is not enabled"))
       if not settings.google_client_id:
           frappe.throw(_("Google Client ID is not configured"))
       # Verify token, extract email, call conversion
   ```

3. **Token verification:** Use Google's public endpoint `https://oauth2.googleapis.com/tokeninfo?id_token=...` — no SDK needed.

4. **Security:** The Google ID token verification replaces OTP — it's equally secure since Google already verified email ownership.

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_social_login (Check, default 0) and google_client_id (Data, 
   depends_on enable_social_login) to Ghost Settings under a "Social Login" 
   Section Break.
2. Create ghost/api/social.py with convert_with_google(ghost_email, id_token). 
   It must: check settings.enable_social_login first, verify the Google ID 
   token via Google's tokeninfo API, validate audience matches google_client_id, 
   extract email, then call convert_to_real_user with OTP bypassed.
3. Add rate limiting to the endpoint.
4. Add tests using a mocked Google response.
```

---

### Feature 5: Soft Lead Capture

**Goal:** Capture a ghost user's email without requiring full OTP verification, enabling abandoned cart recovery.

**Ghost Settings Fields Required:**
- `enable_lead_capture` (Check, default 0) — Toggle lead capture
- `lead_reminder_hours` (Int, default 24, depends_on enable_lead_capture) — Hours before sending reminder
- `lead_reminder_email_template` (Link to Email Template, depends_on enable_lead_capture) — Reminder email template

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/ghost/doctype/ghost_lead/ghost_lead.json` | DocType to store captured emails |
| NEW | `ghost/ghost/doctype/ghost_lead/ghost_lead.py` | Controller |
| NEW | `ghost/api/lead.py` | API to capture and retrieve leads |
| MODIFY | `ghost/hooks.py` | Scheduled task for lead follow-up |
| MODIFY | `ghost/api/ghost.py` | Mark lead as converted on conversion |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add lead capture fields |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - New Tab Break: "Lead Capture"
   - `enable_lead_capture` (Check, default 0)
   - `lead_reminder_hours` (Int, default 24, depends_on `enable_lead_capture`)
   - `lead_reminder_email_template` (Link to Email Template, depends_on `enable_lead_capture`)

2. **Create `Ghost Lead` DocType:**
   - `ghost_email` (Data, Link to User)
   - `captured_email` (Data)
   - `captured_at` (Datetime)
   - `status` (Select: Captured / Converted / Expired)
   - `conversion_reminder_sent` (Check)

3. **API:** `ghost.api.lead.capture_email(ghost_email, email)`:
   ```python
   settings = frappe.get_single("Ghost Settings")
   if not settings.enable_lead_capture:
       frappe.throw(_("Lead Capture is not enabled"))
   ```

4. **Scheduled task:** Check for ghost leads older than `lead_reminder_hours` that haven't converted, send reminder email.

5. **Integration:** When `convert_to_real_user` succeeds, update matching Ghost Lead status to "Converted".

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_lead_capture (Check, default 0), lead_reminder_hours 
   (Int, default 24), and lead_reminder_email_template (Link to Email Template) 
   to Ghost Settings under a "Lead Capture" Tab Break. Use depends_on.
2. Create a "Ghost Lead" DocType with: ghost_email, captured_email, 
   captured_at, status (Captured/Converted/Expired), conversion_reminder_sent.
3. Create ghost/api/lead.py with capture_email(ghost_email, email) — must 
   check settings.enable_lead_capture first.
4. Add a scheduled task that finds leads older than lead_reminder_hours, 
   sends a reminder, and marks conversion_reminder_sent.
5. Update convert_to_real_user to mark matching Ghost Lead as "Converted".
6. Add tests verifying toggle behavior.
```

---

### Feature 6: Multi-Device Ghost Merging

**Goal:** When the same person has ghost sessions on multiple devices, merge all ghost data into one real user on conversion.

**Ghost Settings Fields Required:**
- `enable_multi_device_merge` (Check, default 0) — Toggle multi-device merging
- `merge_detection_method` (Select: Lead Email / Fingerprint / Both, depends_on enable_multi_device_merge)

#### Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| NEW | `ghost/api/merge.py` | Multi-ghost merge logic |
| MODIFY | `ghost/api/ghost.py` | Check for other ghost sessions to merge (guarded by toggle) |
| MODIFY | `ghost/ghost/doctype/ghost_settings/ghost_settings.json` | Add merge fields |

#### Implementation Steps

1. **Add to Ghost Settings:**
   - `enable_multi_device_merge` (Check, default 0)
   - `merge_detection_method` (Select: Lead Email / Fingerprint / Both, depends_on `enable_multi_device_merge`)

2. **Detection:** When converting, if `enable_multi_device_merge`:
   - Check Ghost Lead table for other ghost sessions that captured the same email
   - Optionally check fingerprint matches (if Feature 9 is also enabled)

3. **Merge:** For each related ghost, run `migrate_ghost_data_to_existing_user`.

4. **Response:** Include `merged_ghosts` array in the conversion response.

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_multi_device_merge (Check, default 0) and 
   merge_detection_method (Select) to Ghost Settings.
2. Create ghost/api/merge.py with find_related_ghosts(real_email) and 
   merge_all_ghosts(ghost_emails, real_email).
3. Call from convert_to_real_user ONLY if settings.enable_multi_device_merge.
4. Add merged_ghosts to the response.
5. Add tests verifying toggle behavior and merge logic.
```

---

## Phase 3 — Enterprise & Scale

---

### Feature 7: Conversion Funnel API

**Goal:** Expose conversion metrics as a REST API for external dashboards (Grafana, Metabase).

**Ghost Settings Fields Required:**
- `enable_analytics_api` (Check, default 0) — Toggle the API endpoint

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_analytics_api (Check, default 0) to Ghost Settings.
2. Create ghost/api/analytics.py with get_conversion_funnel(from_date, to_date) 
   that returns: total_sessions, total_conversions, conversion_rate, 
   avg_time_to_convert_ms, conversions_by_mode, daily_breakdown.
3. Guard with: if not settings.enable_analytics_api: frappe.throw(...)
4. Require System Manager role. Add rate limiting. Add tests.
```

---

### Feature 8: Bulk Ghost Cleanup Optimization

**Goal:** Replace per-user `frappe.delete_doc` with batch SQL for large-scale cleanup.

**Ghost Settings Fields Required:**
- `cleanup_batch_size` (Int, default 500) — Number of ghost users to delete per batch

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add cleanup_batch_size (Int, default 500) to Ghost Settings under the 
   Ghost Identity tab.
2. Optimize ghost/tasks.py delete_expired_ghost_users to use batch SQL DELETE 
   instead of per-user frappe.delete_doc. Process in batches of cleanup_batch_size.
3. First delete child table rows (Has Role, User Email, etc), then delete 
   the User rows.
4. Log the count of deleted users. Add tests.
```

---

### Feature 9: Ghost Session Fingerprinting

**Goal:** Reconnect returning anonymous users to their existing ghost session using device fingerprinting.

**Ghost Settings Fields Required:**
- `enable_fingerprinting` (Check, default 0) — Toggle fingerprint matching
- `fingerprint_expiry_days` (Int, default 7, depends_on enable_fingerprinting) — How long to remember a fingerprint

#### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Add enable_fingerprinting (Check, default 0) and fingerprint_expiry_days 
   (Int, default 7) to Ghost Settings.
2. Add an optional fingerprint parameter to create_ghost_session.
3. If enable_fingerprinting and a fingerprint is provided that matches an 
   existing active ghost user, return that ghost's tokens instead of creating 
   a new one.
4. Store fingerprints in a new "Ghost Fingerprint" DocType linked to the 
   ghost user.
5. Add tests verifying toggle behavior.
```

---

## Ghost Settings Summary (All New Fields)

| Feature | Field | Type | Default | Tab/Section |
|---------|-------|------|---------|-------------|
| Analytics | `enable_conversion_logging` | Check | 0 | Analytics |
| Analytics | `conversion_log_retention_days` | Int | 90 | Analytics |
| Webhooks | `enable_webhooks` | Check | 0 | Webhooks & Events |
| Webhooks | `webhook_url` | Data | — | Webhooks & Events |
| Webhooks | `webhook_secret` | Password | — | Webhooks & Events |
| Webhooks | `enable_realtime_events` | Check | 0 | Webhooks & Events |
| Magic Link | `enable_magic_link` | Check | 0 | Conversion Settings |
| Magic Link | `magic_link_expiry_minutes` | Int | 30 | Conversion Settings |
| Magic Link | `magic_link_redirect_url` | Data | — | Conversion Settings |
| Magic Link | `magic_link_email_template` | Link | — | Conversion Settings |
| Social Login | `enable_social_login` | Check | 0 | Conversion Settings |
| Social Login | `google_client_id` | Data | — | Conversion Settings |
| Lead Capture | `enable_lead_capture` | Check | 0 | Lead Capture |
| Lead Capture | `lead_reminder_hours` | Int | 24 | Lead Capture |
| Lead Capture | `lead_reminder_email_template` | Link | — | Lead Capture |
| Multi-Device | `enable_multi_device_merge` | Check | 0 | Ghost Identity |
| Multi-Device | `merge_detection_method` | Select | — | Ghost Identity |
| Funnel API | `enable_analytics_api` | Check | 0 | Analytics |
| Bulk Cleanup | `cleanup_batch_size` | Int | 500 | Ghost Identity |
| Fingerprinting | `enable_fingerprinting` | Check | 0 | Ghost Identity |
| Fingerprinting | `fingerprint_expiry_days` | Int | 7 | Ghost Identity |

---

## Development Workflow Summary

```
┌─────────────────────────────────────────────┐
│  1. Read AGENTS.md                          │
│  2. Branch from develop                     │
│  3. Use AI prompt template from this doc    │
│  4. Review generated code                   │
│  5. Run tests                               │
│  6. Update docs (README, Bruno, AGENTS.md)  │
│  7. Commit with conventional messages       │
│  8. Push & create PR                        │
└─────────────────────────────────────────────┘
```

> [!TIP]
> Each feature is designed to be independently developable. You can hand any single feature section to an AI agent as a self-contained task. The AI prompt templates are written to produce production-ready code on the first pass.
