# Public upgrade and API migration

## Release classification

This candidate contains **breaking authentication changes** relative to public commit
`672dfec9346dfd935c87fdc6ded554014a36d7f4`. Treat it as a major release (2.0 after
pre-release validation), rather than silently replacing 1.0.0. The working branch's
package version is still 1.0.0; no Marketplace release has been published by this work.
A successful migration does not mean all existing clients remain compatible.

Ghost remains independent of ERPNext and usable by any business application.
Existing User records, their passwords and the standard Frappe password login are retained.
Existing verified users keep their roles. Ghost does not migrate arbitrary customer,
cart, booking or other business data into an already existing account automatically.

## What existing integrations must change

| Existing use | Candidate behavior | Required client or administrator action |
| --- | --- | --- |
| GET requests used for authentication writes | Restricted to POST | Send POST with the appropriate bearer or native cookie/CSRF credentials |
| `create_ghost_session(email=...)` | Rejected, including a new caller-selected email | Send no email; save the server-generated identity and issued credentials |
| Fingerprint used to resume an account | Always creates a new anonymous identity | Resume with valid credentials, never with a device fingerprint |
| Eight-character server-generated Ghost identity | Accepted when domain, owner, role, enabled state and Website User type match | Keep its issued credentials; test any custom domain or role configuration |
| Custom caller-named or staff Ghost accounts | Cannot pass the anonymous-source checks | Review separately; authenticate the real account through a verified flow |
| Conversion without OTP, `bypass_otp`, or caller-supplied Google channel | Rejected | Use recipient-bound Conversion OTP, or the actual Google/magic-link endpoint |
| Direct login using a Conversion OTP | Rejected | Request `purpose=Login`; submit the code directly to `ghost.api.auth.login` |
| Validate a code and then call login | Validation consumes the code | Submit once to login/conversion; do not validate separately first |
| Login with both email and phone, or an OTP row containing both | Rejected | Choose exactly one recipient per challenge, including when delivery is `Both` |
| OTP delivery channel `None`, or unbound anonymous OTP generation | Rejected | Configure Email/SMS (Both chooses one recipient); use a separate app-owned challenge if implementing another workflow |
| Public OTP response used to read the code or document ID | Only delivery status/message is public | Obtain the code through email/SMS; do not read `tabOTP` from the frontend |
| Guest CRUD on `OTP` | Removed | Use the whitelisted OTP API; trusted server code can still use native DocType access |
| Login always returns access/refresh tokens | Native cookie session by default | For a headless client, explicitly pass the OAuth client configured in Ghost Settings |
| OTP login already enabled implicitly | New `enable_otp_login` starts disabled on upgrades/fresh installs | Configure delivery and explicitly enable it during the planned cutover |
| Public account creation implicitly enabled | New `allow_public_signup` starts disabled | Explicitly enable signup if that is the installation's policy |
| Staff OTP login | Disabled unless `allow_system_user_login` is enabled; built-in users always denied | Keep native staff login or deliberately opt in after reviewing the policy |
| Fixed-code sandbox used in a browser or staging server | Rejected outside automated tests; normal migration turns it off | Use real delivery; fixed codes are only for automated tests |
| Automatic account merging by captured email/fingerprint | Disabled despite retained legacy configuration | Consumer app must prove ownership of every source before migrating its own data |
| Magic link opened as a Guest, or by another anonymous account | Cannot consume it | Consume using the originating Ghost credentials in the application |
| API response used to obtain a developer magic link | Removed | Use the actual delivered email link/token |
| Browser-origin wildcard used for cookie login | Wildcard is insufficient | Configure the actual trusted portal origin and native cookie/CSRF behavior |
| Reusing an old refresh token | Rejected after a successful rotation | Save the replacement atomically; serialize refresh requests in each client |
| Retrying conversion with revoked anonymous credentials | Rejected | Persist the successful response; if it was lost, authenticate the real account again |
| Conversion webhook/realtime consumed globally | Delivered after commit, realtime scoped to verified user, no credential payload | Subscribe as the verified user and migrate business records in an app-owned handler |

A code change cannot identify every previously mis-issued credential. Before upgrading an
installation that exposed the old unverified issuance paths, plan revocation of affected
OAuth credentials and review sessions/roles. This candidate does not silently revoke all
users on migration. Record the cutover and any required reauthentication in the release notes.

## OTP versus Ghost OTP

**This candidate keeps the internal DocType named `OTP` and table `tabOTP`.**
The Python path `ghost.ghost.doctype.otp.otp` and whitelisted `ghost.api.otp.*` paths are
retained. No existing OTP records are moved or deleted by a naming change.

Renaming a JSON file/controller alone would be unsafe. A future internal rename affects:

- `/api/resource/OTP`, `frappe.get_doc("OTP", ...)`, SQL using `tabOTP`, reports and jobs;
- Link/Dynamic Link fields, Custom Fields, Property Setters, permissions, fixtures,
  scripts and other apps referencing the old DocType;
- Python imports of the controller, Desk routes and saved bookmarks;
- in-flight challenges, naming series, shares, attachments and audit references.

The HTTP methods under `ghost.api.otp` can retain their public names even if the backing
DocType changes, but Frappe does not give old resource URLs and arbitrary SQL a transparent
compatibility alias. A Python import shim alone cannot preserve those contracts.

For this release, a navigation label **Ghost OTP** can distinguish the feature while
keeping its internal name. If an internal rename is approved later, ship it separately:

1. Inventory downstream references and detect whether another app owns a conflicting OTP
   DocType. Do not guess ownership or overwrite another app's table.
2. Prepare a database/files backup and test restoration on a clone of a real installation.
3. Implement an idempotent, versioned migration with Frappe's native DocType rename support
   at the correct schema-sync stage; verify document names, rows and native references.
4. Keep `ghost.api.otp` stable and retain the old Python import with a deprecation notice.
   Publish a migration period for raw DocType/REST/SQL consumers; these require edits.
5. Test fresh install, upgrade, repeated migration, active-code verification, custom fields,
   reports, attachments and downstream apps on supported Frappe branches.
6. Announce the breaking internal name change in a major release. Roll back using the
   tested database/files/code backup; checking out the old Python code is insufficient.

Do not combine that optional naming migration with the current security cutover.

## Deployment sequence

1. Inventory each site's actual Ghost version, consumers, custom Ghost domain/role,
   staff policy, delivery account/template and currently enabled features.
2. Pin the old release and back up the site database/files. Rehearse on a clone; keep a
   tested restore path. Existing-site tests alone do not prove a clean install.
3. Update consumer clients using the table above. Use native Frappe User records and
   app-owned migration handlers; do not add Ecom dependencies to Ghost.
4. Require both Frappe v15/v16 CI jobs (fresh installation and previous-public-commit
   upgrade) to pass. Read the compatibility report for any additional unverified gate.
5. Deploy in a maintenance window, run `bench --site <site> migrate`, configure delivery,
   explicitly set OTP/signup policy, and revoke affected credentials as planned.
6. Verify real mailbox delivery, login, logout, refresh, CSRF and app-specific ownership
   in staging, then smoke-test the live cutover. Google needs actual provider credentials.
7. Publish a versioned changelog and migration notice before Marketplace distribution.
