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
> - The internal **OTP** DocType is retained. Read the
>   [upgrade checklist and full compatibility matrix](docs/API_MIGRATION.md) and
>   [test evidence and remaining release gates](docs/COMPATIBILITY_REPORT.md) before deployment.
>
> The release must carry versioned GitHub and Marketplace upgrade notes before distribution.

## Install and configure

```bash
bench get-app https://github.com/muneeb141/ghost
bench --site your-site install-app ghost
```

In **Ghost Settings**, configure only the features your application uses:

- Anonymous identities: create an OAuth Client, select it, select the Website User role
  `Ghost`, then enable Ghost Feature. Persist the issued credentials securely.
- Email/SMS login: configure the outgoing Email Account/template or SMS provider, then
  explicitly enable OTP Login. Enable Public Signup only if visitors may create accounts.
- Staff OTP login: separately opt in if required; built-in users remain excluded.
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

The internal DocType remains **`OTP`** (`tabOTP`); its Python and public API paths remain.
An internal rename to **Ghost OTP** requires a separate, tested migration and downstream
changes for raw DocType, REST-resource and SQL consumers. It is not part of this candidate.

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
recipient and actual delivered code. Submit focused pull requests against `main`, with
compatibility evidence and migration notes for any public behavior change.

MIT license. Maintainer: Muneeb Mohammed.
