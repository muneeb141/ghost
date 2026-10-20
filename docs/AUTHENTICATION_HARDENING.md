# Ghost authentication repair and integration contract

Date: 2026-10-21. Development branch: `fix/auth-boundaries`, based on upstream
`672dfec9346dfd935c87fdc6ded554014a36d7f4`. This is a local security repair candidate,
not a published release or a claim of a complete security audit.

## Product boundary

Ghost is a reusable Frappe authentication app for any business. It owns OTP proof,
anonymous identities, sessions, credential issuance and controlled identity conversion.
It requires no ERPNext, Ecom, CRM, booking, education or other business app dependency.
Frappe remains the owner of User, Role, sessions and OAuth records. A consuming app owns
its own customer, patient, applicant, booking, cart or other business records and permissions.
A verified email identifies a person; it never by itself grants access to records whose
ownership belongs to someone else. Unrelated businesses should use separate sites.

## Examples of the defects and their effects

These describe paths in the reviewed base source, not evidence of a deployed compromise.

| Defect | Example | Effect | Repair in this candidate |
| --- | --- | --- | --- |
| Existing-email guest session | A visitor names an existing portal user while requesting an anonymous identity | The duplicate-account branch can issue credentials for that existing account without email proof, subject to configured Ghost/OAuth prerequisites | Public email input rejected; full random server-generated identity; duplicate insert must fail |
| Public OTP bypass | A new anonymous visitor requests conversion to another user's email while disabling verification in the request | Conversion can produce credentials for the other account | Public bypass rejected; OTP mandatory; provider verification confined to a private function |
| Magic-link secret in response | A visitor asks for a login link to another person's mailbox and reads the HTTP response | The returned development link removes the need to control that mailbox | Response contains no URL/token; delivery failure fails the operation |
| Unowned source Ghost | A person uses their own valid Google account but names another visitor's anonymous account | A booking or other session data could be attributed to the wrong person even though Google verified the destination account | Source actor must equal the authenticated, enabled anonymous account; Google proof covers the destination only |
| Fingerprint as credential | A copied or shared browser fingerprint is supplied by another device | The old flow can reconnect to the fingerprint's account without its session/token | Fingerprints no longer authenticate or reconnect; clients retain actual credentials |
| OTP guesses or replay | A bot makes many guesses, or two requests submit the same code simultaneously | Issuance limits do not limit guesses; non-atomic consumption permits a race | Redis limits survive DB rollback; recipient and purpose binding; primary-key locking and live-status recheck |
| Guest permissions on OTP | A Guest-capable document route honors the old OTP read/create permissions | Authentication secrets could become accessible or fake OTP records could be created | Guest permissions removed; private metadata not indexed for website search |
| Partial conversion | An error occurs after an internally committed rename or token change | Identity, links and credentials can disagree after failure | Request transaction preserved; native Frappe rename updates User Links; failed issuance rolls back |

The conversion event is now sent to the verified user rather than globally, and webhook
jobs wait for transaction commit. Unverified captured lead emails cannot claim another
session's lead. Matching an email or fingerprint does not trigger automatic cross-device merges.

## Supported flows and API changes

All authentication mutations use POST. Calls retain normal Frappe CSRF/session handling.
Cookie login also rejects untrusted browser Origins; headless browser clients must configure
explicit trusted origins in Frappe allow_cors. A wildcard alone does not authorize cookie login.

1. Configure outgoing email delivery and a Ghost email OTP template in Desk.
2. Enable **Ghost Settings > Enable OTP Login**. Installation alone leaves OTP login off.
3. Enable **Allow Public Signup** only for businesses that accept new public accounts.
   Existing-user-only portals leave it off. Choose a non-Desk Default User Role as needed;
   leaving it blank adds no explicit role. Website User is a User Type, not a guaranteed Role.
4. Send a code with `ghost.api.otp.send_otp`, providing `email` and `purpose: "Login"`.
   The public response never returns the OTP, document name or transport results.
5. Submit the email and code directly to `ghost.api.auth.login`. Do not call
   `validate_otp` first: it consumes the code and does not create a login proof for reuse.
6. The default login response creates a native Frappe session and contains no bearer tokens.
   A native/mobile client may explicitly request the configured OAuth client by `client_id`.
   Keep browser authentication in the HttpOnly session; do not store refresh tokens in localStorage.

Email OTP works with customer addresses at any provider, not just Gmail. Outgoing mail
configuration is different from Google OAuth sign-in. A mailbox code is passwordless
email authentication; it is not a second authentication factor by itself.

Anonymous Ghost identities are optional. Create them only when a consumer actually needs
an authenticated anonymous actor. `create_ghost_session(email=...)` now rejects custom
names. Authenticate subsequent requests using the issued credentials. Conversion requires
that exact source actor and target proof; public OTP conversion uses purpose `Conversion`.
Google and magic-link conversion require source ownership too. Magic links currently require
the original authenticated Ghost session when consumed; an unrelated browser/webview is
rejected. Cross-device conversion needs an explicit source-consent design before restoration.

**Allow System User OTP Login** is off by default. A business must explicitly enable it to
permit its enabled staff accounts to use this passwordless flow. This path does not run the
password-login second-factor challenge. Guest, Administrator and disabled accounts are excluded.

Existing roles are preserved when an anonymous user converts to an existing account.
New users receive only the configured role. Business records with Text/Data ownership
keys need a consuming app's explicit, ownership-checked mapping; native rename can update
User Link fields but cannot infer arbitrary application semantics. Existing-account merges
only reassign the documented Ghost-owned records. Multi-device matching is not proof.

## Ecom integration plan

The user selected Ghost email OTP as a desired Ecom login option. Ghost is installed on
the Ecom Bench and `ecom.localhost`; the repair candidate is applied there for testing.
The storefront adapter and login UI are not implemented by this repair.

- Keep Ecom's existing random HttpOnly guest-cart identity. Product views and cart adds do
  not need a synthetic User or Customer.
- At checkout, ask for email, send a Login OTP, then verify and create a native session.
- Add Ecom Desk authentication choices: Password, Email OTP, or Both. Advertise OTP only
  when the installed Ghost version and delivery configuration meet the contract.
- Respect both Ghost public-signup policy and Ecom customer-signup policy. Configure the
  site-wide Ghost policy deliberately; an Ecom wrapper cannot close a broader Ghost endpoint.
- After successful login, refresh Ecom session/CSRF state, then call the existing cart read
  service to perform its one-time owned merge. Failed verification must not merge anything.
- Ecom creates/links ERP Customer through its own controlled `Customer.portal_users` mapping
  and address workflow. Ghost must not create Customers, invoices, bookings or business records.
- Verify existing/new customer, wrong/expired/replayed OTP, resend/cooldown, disabled account,
  cross-cart denial, overflow/retry, and real phone/desktop cookie behaviour before enabling UI.

## Verification and remaining release gates

Verified on the disposable `ecom.localhost` site with Frappe 16.51.1 / ERPNext 16.50.0.
Verified checks:

- 32 isolated tests (27 boundary checks plus 5 existing profile tests).
- 17 database/Redis tests, including separate-connection OTP and refresh races, rollback,
  account isolation, role preservation, expiry, disabled accounts and private permissions.
- HTTP application smoke: Login OTP creates an HttpOnly session, subsequent authenticated
  request succeeds, no bearer tokens are returned, and a second browser cannot replay the OTP.
- Ecom's 14 existing shopping integration tests passed after Ghost migration.
- Scoped Ruff 0.8.1 and Git whitespace checks passed on all changed/new Python files.
- Final sequential verification repeated migration, all 49 focused Ghost tests and HTTP smoke successfully; log: `/tmp/ghost-auth-final-verification.log`.

The refresh race initially exposed a real range-lock deadlock; resolving the record first,
locking its primary key and rechecking status removed it. The OTP path uses the same approach.
The tested site currently has zero outgoing Email Accounts and no Ghost email account or
template selected. OTP login, public signup, staff OTP login and sandbox are off after tests.
Real mailbox delivery and the Ecom OTP UI are therefore not enabled or claimed verified. Tests use fictitious recipients
and do not send real email/SMS or contact Google. The two-connection tests commit and
remove only their explicit fixtures and restore their configuration changes.

The compatibility follow-up supersedes the earlier test limitations above. See
[the current report](COMPATIBILITY_REPORT.md) and [public upgrade guide](API_MIGRATION.md).
Legacy tests and client examples have been migrated; the complete-suite results and actual
remaining release gates are recorded there. The historical checklist was:

- Update legacy tests/docs that depend on caller-named identities, no-proof conversion,
  fingerprint reconnection or old Login/Conversion OTP semantics. Run the complete suite.
- Verify clean install and upgrade on supported Frappe v15 and v16, not only this existing site.
- Verify actual configured email delivery, browser cookies/CSRF and real Google credentials.
- Revoke previously issued affected OAuth credentials and review active sessions and roles
  on any installation that exposed the old paths; a code fix cannot undo earlier issuance.
- Pin the reviewed release in consuming apps and document the breaking API changes.

The initial repair was local. The compatibility follow-up pushed only the review branch
and ran the CI matrix linked in the current report. No main merge, release publication
or production deployment has been performed.
