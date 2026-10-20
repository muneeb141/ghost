> Local authentication repair candidate: see [the repair contract](docs/AUTHENTICATION_HARDENING.md)
> for the security changes, API migration, tests and remaining release gates. Ghost remains
> a general authentication app; this candidate is not a published release.

# 👻 Ghost — Seamless Anonymous Identity & Conversion Engine for Frappe

**Let users interact anonymously, convert them when they see value.**

Eliminate onboarding friction and supercharge user acquisition across any digital domain. Ghost creates instant anonymous sessions, captures leads mid-journey, and seamlessly converts trial guests into verified customer profiles—preserving every interaction with zero data loss and no unnecessary database bloat.

[![Frappe v15+](https://img.shields.io/badge/Frappe-v15%2B-blue.svg)](https://frappefam.org)
[![Release v1.0.0](https://img.shields.io/badge/Release-v1.0.0-6366f1.svg)](https://github.com/muneeb141/ghost/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-success.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/Docs-GitHub%20Pages-8b5cf6.svg)](https://muneeb141.github.io/ghost/)

---

## ⚡ Quick Start (3 minutes)

```bash
# 1. Fetch & install application onto your local bench site
bench get-app https://github.com/muneeb141/ghost
bench --site your-site install-app ghost

# 2. Enable automated maintenance background workers
bench --site your-site enable-scheduler
```

**Initial Configuration:**
1. Navigate to **Setup > Integrations > OAuth Client** in Frappe desk and create a client (`Authorization Code / Password`).
2. Navigate to **Setup > Ghost Settings**, check `Enable Ghost Feature`, and paste your new OAuth Client ID.

**Verify via CLI:**
```bash
curl -X POST http://your-site:8000/api/method/ghost.api.ghost.create_ghost_session \
  -H "Accept: application/json"
```

---

## ✨ Features (Complete Roster)

| Feature | Description |
|---|---|
| 👻 **Anonymous Sessions** | Instantaneous creation of guest accounts (`ghost_*@guest.local`) with secure OAuth2 bearer access & refresh tokens. |
| 🔑 **OTP Conversion** | Secure 6-digit verification codes delivered via email or pluggable SMS gateways with attempt rate limits and QA sandbox mode. |
| 📊 **Analytics Dashboard** | Dedicated desk interface analyzing session generation rates, successful conversions, drop-offs, and time-to-convert metrics. |
| 🔔 **Event Webhooks** | Fire HTTP POST notifications equipped with cryptographic HMAC secret signing to alert external CRM or automation pipelines. |
| ✉️ **Magic Link** | Frictionless one-click email verification link conversion, removing manual OTP code entry entirely. |
| 🔐 **Social Login (Google)** | Directly convert anonymous sessions by verifying Google OAuth2 ID tokens directly within your backend API. |
| 📧 **Soft Lead Capture** | Capture customer email addresses mid-session without demanding full OTP verification to power automated cart recovery reminders. |
| 📱 **Multi-Device Merge** | Intelligently detect and unify segmented guest browsing activity across desktop, mobile, and tablet browsers. |
| 📈 **Funnel API** | Standardized REST API endpoint exposing time-series conversion metrics formatted for external ingestion by Grafana or Metabase. |
| ⚡ **Bulk Cleanup** | High-performance batch SQL purging routines designed to routinely sweep out expired sessions in 100k+ enterprise database architectures. |
| 🔗 **Fingerprinting** | Device and browser matching to reconnect returning anonymous visitors to their existing active ghost account seamlessly. |

---

## 🚀 How It Works

```
┌────────────────────────────────────────────────────────────────────────┐
│  1. Anonymous Visitor arrives on Web/Mobile App                        │
│     └── Request: create_ghost_session()                                │
│     └── Return:  Bearer Token + temporary ghost_xxxx@guest.local       │
├────────────────────────────────────────────────────────────────────────┤
│  2. Active Browsing & Data Accumulation                                │
│     └── User populates Cart, Favorites, Wishlists using Bearer token   │
│     └── Option: capture_lead_email() triggers abandoned cart reminders │
├────────────────────────────────────────────────────────────────────────┤
│  3. Seamless Verification & Transition                                 │
│     └── Option A: OTP Verification via Email or SMS                    │
│     └── Option B: One-Click Magic Email Link                           │
│     └── Option C: Instant Social Sign-In (Google OAuth ID Token)       │
├────────────────────────────────────────────────────────────────────────┤
│  4. Permanent Account Established (Zero Data Loss!)                    │
│     └── Targeted SQL reassigns all Cart & Wishlist links automatically │
│     └── Real user tokens returned; temporary ghost credentials voided  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 Frontend Integration Preview

Ghost avoids cookies entirely in favor of lightweight standard OAuth2 authorization headers (`Authorization: Bearer <token>`), making it drop-in ready for React, Vue, React Native, and mobile Flutter apps.

```javascript
// 1. Initialize anonymous guest session on page landing
const res = await fetch('/api/method/ghost.api.ghost.create_ghost_session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fingerprint: 'fp_a8b92e' }) // Auto-reconnects returning visitors!
});
const { access_token, user } = (await res.json()).message;
sessionStorage.setItem('access_token', access_token);

// 2. Perform API calls to your eCommerce platform using bearer token
await fetch('/api/method/my_app.cart.add', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` },
  body: JSON.stringify({ item: 'SHOE-001', qty: 1 })
});
```
👉 [**Read our comprehensive Frontend Integration Guide →**](https://muneeb141.github.io/ghost/#frontend)

---

## ⚙️ Configuration Reference (Snapshot)

Ghost enforces a strict techno-functional standard: **every capability is fully configurable by administrators from a centralized dashboard (`Setup > Ghost Settings`)**.

| Setting Field | Type | Description |
|---|---|---|
| `enable_ghost_feature` | Checkbox | Master toggle enabling anonymous account generation APIs. |
| `client_id` | Text | Your application's designated OAuth2 Client Application ID. |
| `enable_fingerprinting` | Checkbox | Reconnects returning anonymous visitors via hardware hash footprint. |
| `verify_otp_on_conversion`| Checkbox | Requires validating a secure 6-digit OTP code before converting users. |
| `enable_lead_capture` | Checkbox | Activates soft email lead saving (`Ghost Lead`) for automated reminders. |
| `enable_webhooks` | Checkbox | Fires external HTTP POST event notifications upon user conversion. |

👉 [**See all 40+ configurable administrative parameters →**](https://muneeb141.github.io/ghost/#settings)

---

## 📚 Complete Documentation

Our extensive documentation site is hosted on GitHub Pages:
### 🌐 [**muneeb141.github.io/ghost**](https://muneeb141.github.io/ghost/)

- **Getting Started & Setup**
- **Universal Industry Applications (E-Commerce, SaaS, Real Estate, EdTech)**
- **Complete API Reference (13 Endpoints)**
- **Ghost Settings Reference (40+ Fields across 7 Tabs)**
- **DocType Schema Matrix & Data Models (6 Custom DocTypes)**
- **Native Desk Analytics Dashboard & Conversion Telemetry**
- **Frontend & SPA Integration Guide**
- **System Architecture & Scheduler Workers**
- **Testing, Sandbox Mode & Bruno Suite**
- **FAQ, Troubleshooting, GDPR Privacy Policy & Support**

---

## 🧪 Testing & Bruno Verification Suite

We include a comprehensive [Bruno API Test Collection](https://www.usebruno.com/) equipped with automatic pre-request variables and post-response script extraction.

```
/apps/ghost/bruno/
├── Create Ghost Session.bru
├── Create Ghost Session (Fingerprint).bru
├── Refresh Token.bru
├── Send OTP (Conversion).bru
├── Convert (Secure).bru
├── Convert (Frictionless).bru
├── Send Magic Link.bru
├── Social Login (Google).bru
├── Capture Lead Email.bru
├── Ghost Analytics.bru
├── Get Conversion Funnel.bru
└── Direct Auth/
    ├── Send OTP.bru
    └── Login.bru
```

👉 [**See bruno/README.md for automated CI testing and test flow instructions →**](bruno/README.md)

---

## 🔐 Security & Retention

- **Zero Unclaimed PII:** Background maintenance tasks routinely sweep and erase expired anonymous guest user profiles and token logs after your configured retention limit (defaulting to 30 days).
- **Rate-Limited Endpoints:** All public API endpoints feature automated attempt limiting and brute-force lockout protections.
- **SQL Injection Prevention:** Targeted high-speed table conversion routines pass through strict identifier validation and parameterized SQL executions.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page or submit pull requests directly to the `develop` branch.

---

## 📜 License

This application is released under the [MIT License](https://opensource.org/licenses/MIT).
