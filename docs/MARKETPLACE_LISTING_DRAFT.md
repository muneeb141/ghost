# Marketplace listing update draft

Status: prepared for maintainer review; **not published**. Use only after the major-release
acceptance gates and explicit publication authorization. No listing/dashboard setting is changed.

## Public listing review

The [published listing](https://cloud.frappe.io/marketplace/apps/ghost), retrieved on 2026-10-21,
still promotes fingerprint reconnection, unverified multi-device merging, direct SQL conversion,
unqualified sub-500ms timing, zero state loss and automatic GDPR compliance. Those statements
must be replaced for this candidate. The long description also repeats large sections.
Its Privacy Policy resource currently resolves to the older general GitHub Pages documentation;
confirm a dedicated approved policy/disclosure URL before updating the listing.

The visible listing already supplies publisher/contact, v15/v16 support, categories, resource
links and screenshots. Their presence does not certify that the Cloud source/release selection,
image content or link targets describe the new release. Check these in the publisher dashboard.

## Proposed fields

- App name: `ghost` (unchanged).
- App title: `Ghost`.
- Short description: Verified OTP login and anonymous identities for Frappe applications
- Compatibility: Frappe v15 and v16, matching the tested release range.
- Category: retain a suitable generic Business category; ecommerce is one possible consumer.
- License: MIT.
- Support: https://github.com/muneeb141/ghost/issues
- Code: https://github.com/muneeb141/ghost
- Documentation: the approved stable README/documentation after release promotion.
- Privacy: the approved public URL for `docs/PRIVACY.md`; a prospective main-branch URL must
  not be entered until the file is published there and the URL is verified.
- Terms/license: verify the actual resource against the MIT license and any service terms
  the publisher offers; do not imply that installing this app provides a hosted service.

An existing suitable square icon is `docs/assets/favicon.png`: inspected, 300 x 300 pixels,
centered ghost symbol without text. The larger `docs/assets/logo.png` is 654 x 686; the square
icon avoids a crop adjustment. Verify the actual uploaded logo, not only this source asset.

## Proposed long description

### Overview

Add anonymous identities and verified passwordless authentication to Frappe portals and
applications. Ghost supports business applications without requiring ERPNext or ecommerce.

### Features

- Email OTP authentication and configurable SMS delivery.
- Optional anonymous identities and conversion to a verified account.
- Administrator controls for public signup and existing staff OTP access.
- Native browser sessions and explicit OAuth credentials for headless clients.
- Optional Google and magic-link conversion with originating-session ownership checks.
- Lead capture, conversion analytics, signed webhooks and configurable retention jobs.

### Usage

Configure delivery and authentication policies in Ghost Settings. Integrate the verified login
flow into your application and choose when an anonymous identity is needed. Applications retain
responsibility for their customer, booking, cart or other business-data ownership and migration.

Account conversion verifies the destination identity and the originating anonymous session.
Matching an entered email or browser fingerprint does not automatically link other sessions.
Magic-link conversion requires the originating session. Delivery providers need site-specific
configuration and verification.

### Existing installations

This major update changes authentication contracts and renames the internal OTP record type to
Ghost OTP through a guarded migration. Review upgrade notes, update integrations and rehearse
backup restoration before updating. Explicitly configure OTP login and signup during cutover.

### Support

Use the listing's Support resource for ordinary bugs and integration questions. Share sensitive
security reports privately with the maintainer; exclude credentials and personal records from
public reports.

## Release update notice

Breaking authentication update: server-generated anonymous identities; mandatory recipient/purpose
verification; POST authentication writes; explicit signup/staff policies; browser cookie login by
default; Ghost OTP schema migration. Update direct DocType/REST/SQL consumers. Fingerprint login,
unverified automatic merging and browser fixed-code testing are removed. Read migration notes and
plan affected-credential reauthentication/revocation before the scheduled upgrade.

## Publication checklist

- [ ] Complete the remaining live-provider, browser and restore acceptance gates.
- [ ] Assign the approved major version and dated release notes.
- [ ] Verify the actual Cloud source branch/revision is the approved stable release, not develop.
- [ ] Replace the duplicated old description and unsupported security/performance claims.
- [ ] Upload current screenshots; omit old bypass/fingerprint-reconnection demonstrations.
- [ ] Verify logo, publisher contact and every support/documentation/privacy/license resource.
- [ ] Update the GitHub Pages deployment source/content as appropriate after authorization.
- [ ] Run the hosted Marketplace audit and resolve its actual report.
- [ ] Obtain explicit maintainer authorization before main promotion/publication.

Source requirements: [publishing guidelines](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines).
