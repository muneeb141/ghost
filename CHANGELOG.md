# Changelog

All notable changes to the Ghost app are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-03

### 🎉 Initial Release — Complete Feature Set
Ghost v1.0.0 ships with a complete anonymous-to-authenticated user conversion platform for Frappe applications.

### Added
  
#### Enterprise Documentation & Marketplace Readiness
- **Interactive Documentation Portal (`/docs`)** — Single-page developer documentation site complete with progressive disclosure navigation, 14 annotated real-world screen captures, 2x2 symmetrical industry use-case grids (E-Commerce, SaaS AI platforms, Real Estate portals, EdTech), and comprehensive DocType database schema matrix tables.
- **Enhanced Desk Analytics Visualizer** — Upgraded the native Frappe Desk **Ghost Analytics** page with real-time KPI metric cards (Session Conversion Rate, Sub-500ms Average Conversion Latency, Merged Sessions), responsive historical timeframe dropdown filters (7/30/90/180 Days), line trend curves, mode bar charts, and multi-channel donut breakdowns.
- **GDPR & Legal Compliance Suite** — Added transparent community support routing, automated data retention privacy explanations, and open-source MIT licensing disclaimers for seamless Frappe Cloud Marketplace deployment.

#### Phase 1 — Core Improvements
- **Conversion Analytics Dashboard** — Track ghost creation rates, conversion rates, and average time-to-convert via the dedicated **Ghost Analytics** desk page (`ghost-analytics`). Includes `Ghost Conversion Log` doctype and automatic daily retention cleanup.
- **Event Webhooks** — Fire HTTP POST webhooks in real time when ghost users convert. Supports configurable `webhook_url`, HMAC signing via `webhook_secret`, and Frappe realtime socket events.
- **Magic Link Conversions** — One-click conversion via email link instead of 6-digit OTP. Includes configurable token expiry, dedicated email template link, and customizable redirect URLs.

#### Phase 2 — Growth & Engagement
- **Social Login Conversion** — Convert ghost users via Google Sign-In using OAuth ID token verification.
- **Soft Lead Capture** — Allow anonymous users to save their email without full OTP verification (`Ghost Lead`). Enables abandoned cart recovery emails with scheduled background lead reminders.
- **Multi-Device Ghost Merging** — Automatically detect and merge related ghost sessions across multiple devices when a user signs in or provides their captured email.

#### Phase 3 — Enterprise & Scale
- **Conversion Funnel API** — REST API endpoint (`get_conversion_funnel`) exposing funnel metrics for ingestion into external BI dashboards (Grafana, Metabase).
- **Bulk Ghost Cleanup Optimization** — Replaced per-user framework deletions with high-performance batch SQL deletes for environments managing 100k+ ghost sessions.
- **Ghost Session Fingerprinting** — Optional device and browser fingerprinting to detect returning anonymous users and reconnect them to their existing ghost session instead of creating duplicates.

#### Core Platform & Architecture
- **OAuth2 Bearer Token Authentication** — Issue, rotate, and invalidate short-lived access and refresh tokens without requiring cookies (optimal for React/Vue SPAs and native iOS/Android mobile apps).
- **OTP Verification** — Configurable email and pluggable SMS delivery with attempt limiting and QA sandbox mode (`sandbox_mode=1`).
- **Targeted SQL Renaming** — Direct SQL conversions on link and child tables to avoid framework table-scan timeouts during user conversion.
- **Idempotent Conversions** — Network drops or duplicate client conversion tries seamlessly return valid tokens without throwing errors.
- **Interactive Playground & Demo** — Built-in interactive frontend test application served at `/ghost`.
- **Bruno API Collection** — Comprehensive API documentation and automated test suite with 13 ready-to-run requests.
- **Automated Test Suite** — Complete testing coverage spanning 15 specialized unit test modules under `ghost/tests/`.
- **Centralized Admin Control** — 40+ configurable toggles and parameters in the `Ghost Settings` single DocType.
