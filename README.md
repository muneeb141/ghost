# Ghost

Anonymous identities and verified passwordless authentication for Frappe applications.
Ghost has no ERPNext or ecommerce dependency. Supported framework range: v15 and v16.

> [!IMPORTANT]
> **Existing installations: read before updating.** This candidate introduces breaking
> authentication changes and requires a planned major-version upgrade. Its package version
> is still 1.0.0 during review; it has not been released to Marketplace.
>
> - Back up the database/files and rehearse the upgrade on a staging clone.
> - Update clients for recipient-bound OTPs, `Login` versus `Conversion` purpose, POST
>   requests, and cookie-session versus explicit bearer-token login.
> - Configure email delivery and explicitly enable **OTP Login** and, if required,
>   **Public Signup**. Both new switches start disabled on existing sites too.
> - Verification bypass, fingerprint login and unverified automatic merging are removed.
>   Plan reauthentication/revocation of credentials affected by the old issuance paths.
> - The internal DocType changes from **OTP** to **Ghost OTP** through a data-preserving
>   migration. Update direct DocType/REST/SQL integrations before cutover. Read the
>   [upgrade checklist and full compatibility matrix](docs/API_MIGRATION.md) and
>   [test evidence and remaining release gates](docs/COMPATIBILITY_REPORT.md) before deployment.
>
> The release must carry versioned GitHub and Marketplace upgrade notes before distribution.

## Branches and release policy

| Branch | Purpose | Intended audience |
| --- | --- | --- |
| `main` | Stable distribution branch; repository default | Public installations using an approved release |
| `develop` | Integration and next-release testing; not a production release | Contributors and disposable staging sites |
| `feat/*`, `fix/*` | Focused changes based on `develop` | Pull requests targeting `develop` |
| `release/*` | Optional release freeze and final verification | Release reviewers |

Changes flow through feature/fix PRs into `develop`, then a maintainer-reviewed release PR
into `main`. Passing CI never merges or publishes code automatically. Promotion to `main`
requires the maintainer's explicit release authorization. Keep `main` as the default branch;
contributors select `develop` as their PR base. Branch protection is configured separately
in GitHub; the workflows alone do not enforce it.

The current `main` still contains the older public code. It does **not** contain this
candidate's authentication repairs or OTP rename yet. Existing installations should review
the security changes and arrange the documented cutover; the stable branch name alone is
not a security certification. Release promotion is pending validation and authorization.

For candidate testing only, on a disposable staging Bench:

```bash
bench get-app --branch develop https://github.com/muneeb141/ghost
```

See [contributor workflow](CONTRIBUTING.md), [authentication design and roadmap](docs/AUTH_DESIGN.md),
and [Marketplace review and release gates](docs/MARKETPLACE_REVIEW.md).

## Install and configure

```bash
bench get-app --branch main https://github.com/muneeb141/ghost
bench --site your-site install-app ghost
```

In **Ghost Settings**, configure only the features your application uses:

- Anonymous identities: create an OAuth Client, select it, select the Website User role
  `Ghost`, then enable Ghost Feature. Persist the issued credentials securely.
- Email/SMS login: configure the outgoing Email Account/template or SMS provider, then
  explicitly enable OTP Login. Enable Public Signup only if visitors may create accounts.
- Staff OTP login: separately opt in for existing staff if required; built-in users remain excluded.
  Public signup always requires a role without Desk access, even when staff login is enabled.
- Google conversion and magic links: configure and enable each provider separately.
  Both require the originating anonymous identity's credentials.
- Conversion webhooks/hooks and analytics: optional; business-data reassignment belongs
  to the consuming application and must check ownership.

Fixed-code sandbox authentication works only inside automated tests.

## Authentication flows

### Same-origin portal: native Frappe cookie session

Request `POST /api/method/ghost.api.otp.send_otp`:

```json
{"email": "person@example.com", "purpose": "Login"}
```

Then submit the delivered code **once**, directly to
`POST /api/method/ghost.api.auth.login`:

```json
{"email": "person@example.com", "otp": "<delivered code>"}
```

Login sets the native HttpOnly session cookie and returns the authenticated user.
It does not return bearer tokens by default. Use same-origin credentials and Frappe's
CSRF token on subsequent authenticated writes. Explicit trusted origins are required
for cross-origin browser login; a wildcard is insufficient.

### Headless application: bearer credentials

`POST /api/method/ghost.api.ghost.create_ghost_session` with no email creates a fresh
server-named anonymous Website User and returns access/refresh credentials. A fingerprint
never resumes another identity. Authorize owned calls using `Authorization: Bearer <token>`.

To convert that identity, request a `Conversion` OTP for the real email and call
`ghost.api.ghost.convert_to_real_user` with `ghost_email`, `real_email` and `otp_code`.
Alternatively, use `ghost.api.auth.login` with a `Login` OTP and the configured `client_id`
when replacement bearer credentials are needed. Serialize refresh calls and save each
replacement pair from `ghost.api.auth.refresh_bearer_token` atomically.

Google conversion uses `ghost.api.social.convert_with_google` with the originating
Ghost bearer, `ghost_email` and the actual Google `id_token`. Magic-link consumption uses
`ghost.api.magic_link.consume_magic_link` with the originating Ghost credentials and the
emailed `token`; opening a link as an unrelated Guest is insufficient. The demo accepts
the emailed link in its original authenticated tab.

New target users use native Frappe rename so native User Link fields follow. When the
target already exists, roles are retained and only Ghost-owned references are reassigned;
other applications must implement their own verified migration policy.

## Existing sites and the OTP name

This branch renames the internal DocType from **`OTP`** (`tabOTP`) to **`Ghost OTP`**
(`tabGhost OTP`). A versioned patch runs before model sync and uses Frappe's native rename
so existing record names, values and native references are preserved. The `OTP-...` document
naming series remains unchanged. Conflicting schemas/tables stop migration; they are not merged.

Public **`ghost.api.otp.*`** endpoints stay unchanged. The old Python controller import remains
as a deprecated compatibility alias; new imports use `ghost.ghost.doctype.ghost_otp.ghost_otp`.
Direct `frappe.get_doc("OTP", ...)`, `/api/resource/OTP`, `tabOTP` SQL, hard-coded scripts,
query reports and old Desk bookmarks require updates. There is no transparent REST/SQL alias.
Back up database/files, stop traffic and jobs during cutover, and test on a staging clone first.
Restore the matching database/files/code backup to roll back; an old-code checkout alone is unsafe.

Verification bypasses, caller-selected identities, fingerprint login and unverified
multi-device merging are intentionally removed. Existing integrations using them need
changes. OTP login and signup policy require an explicit cutover configuration.
See the [migration matrix and deployment sequence](docs/API_MIGRATION.md).

## Verification and contribution

Only run fixture-producing checks on an explicitly disposable site:

```bash
bench --site test-site set-config allow_tests true
bench --site test-site migrate
bench --site test-site run-tests --app ghost
env/bin/python apps/ghost/scripts/smoke_email_otp.py test-site
bench build --app ghost
```

The suite includes real database ownership/rollback tests, two-connection OTP/refresh
races, loopback SMTP delivery and raw HTTP webhook signatures. Unit/provider tests use
mocks where described in the [report](docs/COMPATIBILITY_REPORT.md).

The GitHub Actions matrix covers Frappe-only v15/v16 clean installation and upgrades
from the previous public commit. A configured workflow is not evidence that it has run;
require both matrix jobs to pass before merging or distributing a release.

Use the [Bruno collection](bruno/README.md) for manual API checks with your own test
recipient and actual delivered code. Submit focused feature/fix pull requests against `develop`, with
compatibility evidence and migration notes for any public behavior change.

MIT license. Maintainer: Muneeb Mohammed.
