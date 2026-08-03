# Ghost App — Documentation & README Development Plan

> This document is a playbook for creating professional documentation for the Ghost app. Each section contains the **what**, **why**, **where** (exact files), **how** (step-by-step), and **content outlines** so you can hand each task to an AI agent and get consistent, production-quality results.

---

## Current Status

> [!IMPORTANT]
> **Last Updated:** 2026-08-03 | **Updated By:** AI Consultant
> 
> This section must be updated every time a deliverable's status changes. Use the statuses below:
> - 🔴 `Not Started` — No work has begun
> - 🟡 `In Progress` — Actively being developed
> - 🟢 `Completed` — Written, reviewed, and merged
> - 🔵 `In Review` — Written, awaiting review/PR merge

| # | Deliverable | Status | Branch | Notes |
|---|-------------|--------|--------|-------|
| 1 | GitHub Pages Documentation Site | 🔴 Not Started | `docs/ghost-documentation` | Uses Jekyll or plain HTML/CSS |
| 2 | Clean README.md | 🔴 Not Started | `docs/ghost-documentation` | Concise, links to full docs |
| 3 | Updated Bruno README | 🔴 Not Started | `docs/ghost-documentation` | All 13 Bruno files documented |
| 4 | CHANGELOG.md | 🔴 Not Started | `docs/ghost-documentation` | v1.0.0 release notes |
| 5 | Screenshots & Visual Assets | 🔴 Not Started | `docs/ghost-documentation` | Ghost Settings, Analytics, Demo UI |
| 6 | Cleanup & Versioning | 🔴 Not Started | `docs/ghost-documentation` | Remove dead files, set v1.0.0 |

**Completed:** 0/6 &nbsp;|&nbsp; **In Progress:** 0/6

### Changelog
| Date | Deliverable | Change | By |
|------|-------------|--------|-----|
| 2026-08-03 | — | Initial documentation plan created | AI Consultant |

---

## Ground Rules for Documentation Development

> [!IMPORTANT]
> Every AI session working on this documentation **must** read `AGENTS.md` before writing any content. It contains the architecture context and the complete list of features, endpoints, and doctypes.

### Before Starting Any Deliverable
1. **Read** `AGENTS.md` for architecture context and full feature list
2. **Check** `ghost/api/` to see the actual function signatures and docstrings
3. **Check** `ghost/ghost/doctype/ghost_settings/ghost_settings.json` for the full list of settings fields
4. **Branch** from `develop` with branch name: `docs/ghost-documentation`
5. **Commit** with conventional commit messages: `docs: ...`

### Quality Standards
- All code examples must be **copy-paste ready** and **tested**
- All internal links must resolve correctly (both on GitHub and GitHub Pages)
- Use consistent formatting: GitHub Flavored Markdown
- Screenshots should be high-quality, cropped to relevant area, with no personal data visible
- Every API endpoint must include request, response, and error examples

---

## Existing Files Inventory

> [!NOTE]
> Reference this to understand what exists today vs. what needs to be created or replaced.

| File | Status | Action |
|------|--------|--------|
| `README.md` | Outdated — only covers ~30% of features | REWRITE |
| `bruno/README.md` | Outdated — missing 9 Bruno files | REWRITE |
| `docs/index.html` | Old static demo page, not documentation | DELETE |
| `CHANGELOG.md` | Does not exist | CREATE |
| `ghost/__init__.py` | Contains `__version__ = "2.0.0"` | MODIFY → `"1.0.0"` |
| `ghost/create_fingerprint_doctype.py` | One-time setup script, no longer needed | DELETE |

---

## Deliverable 1: GitHub Pages Documentation Site

**Goal:** Create a modern, clean, professional documentation site hosted via GitHub Pages from the `docs/` folder.

### Technology Choice

Use a **single-page static HTML/CSS/JS documentation site** (no build tools, no Jekyll dependency). This is the simplest approach that works directly with GitHub Pages and gives full design control.

**Design Requirements:**
- Modern dark theme with clean typography (Inter or similar Google Font)
- Sticky sidebar navigation on desktop, collapsible on mobile
- Smooth scroll between sections
- Syntax-highlighted code blocks
- Responsive layout (mobile-friendly)
- Copy-to-clipboard buttons on code blocks
- Search functionality (optional, nice-to-have)

### Files to Create

| Action | File | Purpose |
|--------|------|---------|
| DELETE | `docs/index.html` | Remove old static demo page |
| NEW | `docs/index.html` | Main documentation site (single-page with sidebar nav) |
| NEW | `docs/style.css` | Documentation styling |
| NEW | `docs/script.js` | Navigation, syntax highlighting, copy buttons |
| NEW | `docs/assets/screenshots/` | Directory for screenshot images |
| NEW | `docs/assets/logo.svg` | Ghost logo/icon (optional) |

### Documentation Sections (Content Outline)

The single `index.html` page should contain these sections, each reachable via sidebar navigation and anchor links:

#### Section 1: Hero / Introduction
```
- Ghost tagline: "Let users browse anonymously, convert them when they're ready."
- One-line description
- Install command
- Badge links (License, Frappe version, GitHub stars)
- "Get Started" and "View on GitHub" buttons
```

#### Section 2: Getting Started
```
- Prerequisites: Frappe v15+, bench, Python 3.10+, MariaDB
- Installation:
  bench get-app https://github.com/muneeb141/ghost
  bench --site your-site install-app ghost
- Initial Setup:
  1. Create OAuth Client (Setup > Integrations > OAuth Client)
  2. Enable Ghost (Setup > Ghost Settings → paste Client ID)
  3. Enable the scheduler: bench --site your-site enable-scheduler
- Quick Test:
  curl -X POST http://your-site:8000/api/method/ghost.api.ghost.create_ghost_session
- Expected response JSON
```

#### Section 3: How It Works
```
- Flow diagram (ASCII or SVG):
  Anonymous User → Create Ghost Session → Browse with Bearer Token → Ready to Convert → OTP/Magic Link/Google → Real User (all data preserved)
- Explanation of the two conversion paths:
  - Rename path (ghost user doesn't exist as real user)
  - Manual migration path (real user already exists)
- Token lifecycle diagram
```

#### Section 4: Features
```
For each of the 11 features, include:
- Feature name and icon
- One-line description
- How to enable (Ghost Settings field name)
- Code example showing the API call
- Screenshot of the relevant Ghost Settings section

Features to document:
1.  Ghost Sessions — Anonymous user creation with OAuth tokens
2.  OTP Verification — 6-digit code via email/SMS for conversion
3.  Conversion Analytics — Dashboard + conversion logging
4.  Event Webhooks — Real-time HTTP POST on conversion
5.  Magic Link Conversion — One-click email link conversion
6.  Social Login (Google) — Convert via Google Sign-In
7.  Soft Lead Capture — Save email without full conversion
8.  Multi-Device Merging — Merge ghost sessions across devices
9.  Conversion Funnel API — REST API for external dashboards
10. Bulk Ghost Cleanup — High-performance batch SQL cleanup
11. Session Fingerprinting — Reconnect returning anonymous users
```

#### Section 5: API Reference
```
For EVERY whitelisted endpoint, document:

Format per endpoint:
  ### endpoint_name
  **Method:** POST
  **URL:** /api/method/ghost.api.module.function_name
  **Auth:** Guest / Bearer Token / System Manager
  **Rate Limit:** X requests per hour

  **Parameters:**
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|

  **Success Response (200):**
  ```json
  { ... }
  ```

  **Error Response (4xx):**
  ```json
  { ... }
  ```

Complete endpoint list:
1.  ghost.api.ghost.create_ghost_session(email=None, fingerprint=None)
2.  ghost.api.ghost.convert_to_real_user(ghost_email, real_email, first_name, last_name, otp_code, bypass_otp)
3.  ghost.api.auth.login(otp, email, mobile_no, first_name, last_name, client_id)
4.  ghost.api.auth.refresh_bearer_token(refresh_token)
5.  ghost.api.otp.send_otp(email, phone, purpose, user)
6.  ghost.api.otp.validate_otp(otp_code, email, phone, purpose)
7.  ghost.api.magic_link.send_magic_link(ghost_email, real_email)
8.  ghost.api.magic_link.consume_magic_link(token)
9.  ghost.api.social.convert_with_google(ghost_email, id_token)
10. ghost.api.lead.capture_email(email, ghost_email)
11. ghost.api.analytics.get_conversion_funnel(from_date, to_date)
```

#### Section 6: Ghost Settings Reference
```
Document EVERY field in Ghost Settings, organized by tab:

Tab: Ghost Identity
- enable_ghost_feature (Check, default 0)
- enable_auto_cleanup (Check)
- cleanup_batch_size (Int, default 500)
- ghost_role (Link → Role)
- ghost_email_domain (Data, default "guest.local")
- expiration_days (Int, default 30)
- enable_fingerprinting (Check, default 0)
- fingerprint_expiry_days (Int, default 7)
- default_user_role (Link → Role)
- client_id (Data)
- verify_otp_on_conversion (Check)
- enable_social_login (Check)
- google_client_id (Data)
- enable_magic_link (Check)
- magic_link_expiry_minutes (Int)
- magic_link_redirect_url (Data)
- magic_link_email_template (Link → Email Template)

Tab: OTP Configuration
- expiry_time_minutes (Int)
- allow_anonymous_otp (Check)
- sandbox_mode (Check)
- sandbox_otp (Data)
- max_otp_attempts (Int)
- otp_length (Int)
- otp_code_type (Select)
- otp_delivery_type (Select)
- email_account (Link)
- email_template (Link)
- sms_sender (Data)

Tab: OAuth Token Settings
- access_token_expiry_seconds (Int)
- refresh_token_expiry_days (Int)
- ghost_token_scope (Data)
- invalidate_ghost_tokens_on_conversion (Check)

Tab: Lead Capture
- enable_lead_capture (Check)
- lead_doctype, lead_email_fieldname, lead_ghost_fieldname
- lead_status_fieldname, lead_captured_status, lead_converted_status
- lead_reminder_hours (Int)
- lead_reminder_email_template (Link)
- enable_multi_device_merge (Check)
- merge_detection_method (Select)

Tab: Analytics
- enable_conversion_logging (Check)
- conversion_log_retention_days (Int, default 90)
- enable_analytics_api (Check)
- analytics_api_docs (HTML, read-only)

Tab: Integrations (Webhooks)
- enable_webhooks (Check)
- webhook_url (Data)
- webhook_secret (Password)
- enable_realtime_events (Check)
```

#### Section 7: Frontend Integration Guide
```
- JavaScript/React/Vue copy-paste example (full flow)
- How to integrate device fingerprinting from the frontend
- Token management best practices (storage, refresh, expiry)
- Webhook consumer example (Node.js/Python)
- Mobile app integration notes (React Native, Flutter)
```

#### Section 8: Architecture
```
- System overview diagram (use SVG or ASCII art)
- DocType relationships:
  - Ghost Settings (Single)
  - OTP (stores codes)
  - Ghost Conversion Log (audit trail)
  - Ghost Lead (soft captures)
  - Ghost Fingerprint (session continuity)
- Scheduled tasks table with frequency
- Security model overview
```

#### Section 9: Testing
```
- How to run tests: bench --site [site] run-tests --app ghost
- Test file inventory (15 test files)
- Bruno collection overview with link
- Sandbox mode for QA
```

#### Section 10: Troubleshooting / FAQ
```
- Common errors and fixes
- "OAuth Client ID is required"
- "Invalid token" / token refresh
- "OTP Code required"
- Scheduler not running
- Ghost users not being cleaned up
```

### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Delete docs/index.html (old static demo page).
2. Create a modern single-page documentation site at docs/index.html with:
   - Dark theme, Inter font, sticky sidebar navigation
   - Responsive layout (mobile-friendly)
   - Syntax-highlighted code blocks with copy buttons
   - Smooth scrolling between sections
3. Create docs/style.css for all styling.
4. Create docs/script.js for navigation, code highlighting, and copy buttons.
5. Populate ALL sections listed in the documentation plan with real
   content from the actual codebase. Do NOT use placeholder text.
6. Every API endpoint must include the actual function signature from
   ghost/api/*.py, with real request/response examples.
7. Every Ghost Settings field must be documented from
   ghost/ghost/doctype/ghost_settings/ghost_settings.json.
8. Include screenshots from docs/assets/screenshots/ where specified.
```

---

## Deliverable 2: Clean README.md

**Goal:** Rewrite `README.md` to be concise, scannable, and impressive. It should highlight ALL features and link to the full documentation site for details.

### Files to Modify

| Action | File | Purpose |
|--------|------|---------|
| REWRITE | `README.md` | Clean, concise project README |

### Content Outline

```markdown
# 👻 Ghost

**Let users browse anonymously, convert them when they're ready.**

[One-line pitch] + Install command

[Badges: License, Frappe version, v1.0.0, GitHub Pages docs link]

---

## ⚡ Quick Start (3 minutes)
[Keep the existing quick start — it's great]

---

## ✨ Features

[Grid or table showing ALL 11 features with icons and one-line descriptions]

| Feature | Description |
|---------|-------------|
| 👻 Ghost Sessions | Instant anonymous user sessions with OAuth2 tokens |
| 🔑 OTP Conversion | Secure 6-digit code verification via email/SMS |
| 📊 Analytics Dashboard | Track conversion rates, funnel metrics, and trends |
| 🔔 Event Webhooks | Real-time HTTP notifications on conversion events |
| ✉️ Magic Link | One-click conversion via email link |
| 🔐 Social Login | Convert via Google Sign-In |
| 📧 Lead Capture | Save emails without full conversion for cart recovery |
| 📱 Multi-Device Merge | Merge ghost sessions across devices |
| 📈 Funnel API | REST API for Grafana/Metabase dashboards |
| ⚡ Bulk Cleanup | High-performance batch deletion for scale |
| 🔗 Fingerprinting | Reconnect returning anonymous users seamlessly |

---

## 🚀 How It Works
[Keep the existing ASCII flow diagram — it's clear]
[Add one line about fingerprinting reconnection]

---

## 📱 Frontend Integration
[Short 10-line JavaScript example]
[Link to full docs: "See the complete Frontend Integration Guide →"]

---

## ⚙️ Configuration
[Updated settings table with key new fields]
[Link to full docs: "See all 40+ configuration options →"]

---

## 📚 Documentation
[Link to GitHub Pages site]
- Getting Started
- API Reference (12 endpoints)
- Ghost Settings Reference (40+ fields)
- Feature Guide
- Architecture
- Frontend Integration
- Testing Guide

---

## 🎮 Test It Out
[Updated Bruno list showing all 13 requests]
[Link to Bruno README]

---

## 🔐 Security
[Keep existing security section]

---

## 🤝 Contributing
[Keep existing contributing section]

---

## 📜 License
MIT License

---

## 💬 Support
[GitHub Issues, Discussions, Full Docs link]
```

### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Rewrite README.md to match the content outline in the documentation plan.
2. Keep the punchy intro, quick start, and ASCII flow diagram from the
   existing README — they are well-written.
3. Add a complete Feature table showing all 11 features with icons.
4. Update the Configuration table with key new settings.
5. Update the Bruno testing section to show all 13 requests.
6. Add a Documentation section linking to the GitHub Pages site.
7. Keep it concise — link to full docs instead of duplicating content.
8. Add a v1.0.0 badge.
```

---

## Deliverable 3: Updated Bruno README

**Goal:** Document all 13 Bruno request files with proper descriptions and testing flows.

### Files to Modify

| Action | File | Purpose |
|--------|------|---------|
| REWRITE | `bruno/README.md` | Complete Bruno collection documentation |

### Content Outline

```markdown
# Ghost API — Bruno Test Collection

## About
[Brief description of Ghost]

## Prerequisites
[Installation + Ghost Settings configuration]

## Setup
[Update baseUrl instructions]

## Complete Request Inventory

| # | Request | Auth | Description |
|---|---------|------|-------------|
| 1 | Create Ghost Session | Guest | Creates anonymous user + tokens |
| 2 | Create Ghost Session (Fingerprint) | Guest | Creates or reconnects via fingerprint |
| 3 | Refresh Token | Bearer | Rotates expired access tokens |
| 4 | Send OTP (Conversion) | Guest | Sends OTP to real email |
| 5 | Convert (Secure) | Bearer | Converts with OTP verification |
| 6 | Convert (Frictionless) | Bearer | Converts without OTP (bypass) |
| 7 | Send Magic Link | Guest | Sends magic link email |
| 8 | Social Login (Google) | Guest | Converts via Google ID token |
| 9 | Capture Lead Email | Bearer | Saves lead email without conversion |
| 10 | Ghost Analytics | Bearer | Gets analytics dashboard data |
| 11 | Get Conversion Funnel | Bearer | Gets funnel metrics for external dashboards |

## Test Flows

### Flow 1: Basic Ghost → OTP → Convert
1. Create Ghost Session
2. Send OTP (Conversion)
3. Convert (Secure)

### Flow 2: Ghost → Magic Link Convert
1. Create Ghost Session
2. Send Magic Link

### Flow 3: Ghost → Google Convert
1. Create Ghost Session
2. Social Login (Google)

### Flow 4: Fingerprint Reconnection
1. Create Ghost Session (Fingerprint) — first time
2. Create Ghost Session (Fingerprint) — same fingerprint returns same user

### Flow 5: Lead Capture
1. Create Ghost Session
2. Capture Lead Email

### Flow 6: Analytics
1. Ghost Analytics
2. Get Conversion Funnel

## Variables
[Table of auto-populated variables: ghost_email, access_token, etc.]
```

### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Rewrite bruno/README.md to document all 13 Bruno request files.
2. List every .bru file with its auth type and description.
3. Include 6 test flows showing the recommended order of requests.
4. Document the auto-populated variables from post-response scripts.
5. Include setup instructions for baseUrl configuration.
```

---

## Deliverable 4: CHANGELOG.md

**Goal:** Create a professional changelog documenting v1.0.0 with all 9 features.

### Files to Create

| Action | File | Purpose |
|--------|------|---------|
| NEW | `CHANGELOG.md` | Version history and release notes |

### Content Outline

```markdown
# Changelog

All notable changes to the Ghost app are documented in this file.

## [1.0.0] - 2026-08-03

### 🎉 Initial Release — Complete Feature Set

Ghost v1.0.0 ships with a complete anonymous-to-authenticated user
conversion platform for Frappe applications.

### Added

#### Phase 1 — Core Improvements
- **Conversion Analytics Dashboard** — Track ghost creation rates,
  conversion rates, and average time-to-convert via the Ghost Analytics
  desk page. Includes `Ghost Conversion Log` doctype and daily
  retention cleanup.
- **Event Webhooks** — Fire HTTP POST webhooks when ghost users convert.
  Supports `webhook_url`, `webhook_secret` (HMAC signing), and
  Frappe realtime events.
- **Magic Link Conversions** — One-click conversion via email link
  instead of 6-digit OTP. Configurable expiry and redirect URL.

#### Phase 2 — Growth & Engagement
- **Social Login Conversion** — Convert ghost users via Google Sign-In
  using ID token verification.
- **Soft Lead Capture** — Let ghost users save their email without full
  OTP verification. Enables abandoned cart recovery emails with
  scheduled lead reminders.
- **Multi-Device Ghost Merging** — Automatically detect and merge ghost
  sessions when a user has sessions across multiple devices.

#### Phase 3 — Enterprise & Scale
- **Conversion Funnel API** — REST API endpoint exposing funnel metrics
  for external dashboards (Grafana, Metabase).
- **Bulk Ghost Cleanup Optimization** — Replaced per-user
  `frappe.delete_doc` with batch SQL deletes for 100x faster cleanup
  in high-volume environments.
- **Ghost Session Fingerprinting** — Optional device fingerprinting to
  reconnect returning anonymous users to their existing ghost session.

#### Core Platform
- OAuth2 bearer token authentication (access + refresh tokens)
- OTP verification via email/SMS with sandbox mode
- Targeted SQL renames for production-safe conversions
- Interactive API playground at /ghost
- Bruno API test collection (13 requests)
- 15 automated test files
- Rate limiting on all endpoints
- Comprehensive Ghost Settings with 40+ configurable fields
```

### AI Prompt Template
```
Read AGENTS.md first. Then:
1. Create CHANGELOG.md at the project root.
2. Document v1.0.0 with all 9 features organized by phase.
3. Include a "Core Platform" section for the base features.
4. Follow the Keep a Changelog format (https://keepachangelog.com).
```

---

## Deliverable 5: Screenshots & Visual Assets

**Goal:** Capture screenshots of the Ghost Settings UI, Analytics Dashboard, and Demo UI to embed in the documentation.

### Screenshots Required

| # | Screenshot | What to Capture | Save As |
|---|-----------|----------------|---------|
| 1 | Ghost Settings — Ghost Identity Tab | The main tab showing enable_ghost_feature, ghost_role, fingerprinting, etc. | `docs/assets/screenshots/settings-ghost-identity.png` |
| 2 | Ghost Settings — OTP Configuration Tab | OTP settings with sandbox mode, delivery type | `docs/assets/screenshots/settings-otp.png` |
| 3 | Ghost Settings — OAuth Token Settings Tab | Token expiry, scope, invalidation | `docs/assets/screenshots/settings-oauth.png` |
| 4 | Ghost Settings — Lead Capture Tab | Lead capture and multi-device merge settings | `docs/assets/screenshots/settings-lead-capture.png` |
| 5 | Ghost Settings — Analytics Tab | Conversion logging, funnel API, docs | `docs/assets/screenshots/settings-analytics.png` |
| 6 | Ghost Settings — Integrations Tab | Webhook URL, secret, realtime events | `docs/assets/screenshots/settings-integrations.png` |
| 7 | Ghost Analytics Page | The desk page showing conversion metrics | `docs/assets/screenshots/analytics-dashboard.png` |
| 8 | Demo UI — Ghost Playground | The /ghost page showing the interactive API playground | `docs/assets/screenshots/demo-playground.png` |
| 9 | Bruno Collection | Bruno app showing the request list | `docs/assets/screenshots/bruno-collection.png` |

### How to Capture

Use the browser subagent to:
1. Navigate to `http://huf-reason.localhost:8000/app/ghost-settings`
2. Screenshot each tab
3. Navigate to `http://huf-reason.localhost:8000/app/ghost-analytics`
4. Screenshot the dashboard
5. Navigate to `http://huf-reason.localhost:8000/ghost`
6. Screenshot the demo playground
7. Save all screenshots to `docs/assets/screenshots/`

### AI Prompt Template
```
1. Use the browser subagent to navigate to each Ghost Settings tab and
   capture screenshots.
2. Ensure you are logged in as Administrator before capturing.
3. Save all screenshots to docs/assets/screenshots/ with the filenames
   specified in the documentation plan.
4. Crop screenshots to show only the relevant content area, not the
   full browser window or Frappe desk sidebar.
```

---

## Deliverable 6: Cleanup & Versioning

**Goal:** Remove dead files and set the version to v1.0.0.

### Files to Modify/Delete

| Action | File | Change |
|--------|------|--------|
| DELETE | `docs/index.html` | Old static demo page (replaced by new docs site) |
| DELETE | `ghost/create_fingerprint_doctype.py` | One-time setup script already executed |
| MODIFY | `ghost/__init__.py` | Change `__version__` from `"2.0.0"` to `"1.0.0"` |

### AI Prompt Template
```
1. Delete docs/index.html (old static demo, being replaced).
2. Delete ghost/create_fingerprint_doctype.py (one-time setup script).
3. Update ghost/__init__.py: change __version__ from "2.0.0" to "1.0.0".
4. Commit with: docs: cleanup dead files and set version to v1.0.0
```

---

## Development Workflow

```
┌─────────────────────────────────────────────┐
│  1. Read AGENTS.md                          │
│  2. Branch: docs/ghost-documentation        │
│  3. Execute deliverables in order (1→6)     │
│  4. Deliverable 5 (Screenshots) should be   │
│     done AFTER Deliverable 6 (Cleanup) so   │
│     the settings UI is in its final state   │
│  5. Commit frequently with docs: prefix     │
│  6. Push & merge to develop                 │
└─────────────────────────────────────────────┘
```

### Recommended Execution Order

1. **Deliverable 6** (Cleanup & Versioning) — Quick wins, removes dead files
2. **Deliverable 4** (CHANGELOG.md) — Quick, standalone file
3. **Deliverable 5** (Screenshots) — Capture from clean UI
4. **Deliverable 1** (GitHub Pages Site) — The big one, uses screenshots
5. **Deliverable 3** (Bruno README) — Standalone, can parallel with #4
6. **Deliverable 2** (README.md) — Last, because it links to GitHub Pages

---

## GitHub Pages Setup

After the docs site is created, enable GitHub Pages:

1. Go to the GitHub repository → Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: `develop` (or `main`), folder: `/docs`
4. Save

The documentation will be available at: `https://muneeb141.github.io/ghost/`

> [!TIP]
> Each deliverable is designed to be independently executable. You can hand any single deliverable section to an AI agent as a self-contained task. The AI prompt templates are written to produce production-ready content on the first pass.
