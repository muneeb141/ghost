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

## OTP to Ghost OTP: internal schema migration

The `fix/ghost-otp-rename` candidate builds on `fix/auth-boundaries` and renames Ghost's
internal DocType **`OTP`** (`tabOTP`) to **`Ghost OTP`** (`tabGhost OTP`). This is part of
the planned breaking major update; it is not a published Marketplace release.

### Automatic migration

`ghost.patches.v2_0.rename_otp_to_ghost_otp` runs **before model sync**. It checks ownership
and table state, then uses Frappe's native DocType rename. It preserves existing OTP record
names and values, including expiry/status, and leaves the existing `OTP-...` naming series
and counter in use. The new controller is `ghost.ghost.doctype.ghost_otp.ghost_otp.GhostOTP`.

Native Link metadata and DocType references are updated by Frappe, including Custom Fields,
Property Setters, attachment references, shares, comments and version references. Serialized
code/query text and external applications are not rewritten. Consumer apps with versioned
metadata must update their own definitions too, or their later sync can restore old references.

The patch is a no-op on a fresh site or after a successful rename. It refuses to merge two
existing OTP schemas or overwrite a foreign/custom DocType or an orphan table. Before-install
and before-migrate preflights prevent model sync from bypassing these checks; do not use
`--skip-failing` to work around a conflict. A foreign `OTP` may coexist after Ghost has its
own correctly owned `Ghost OTP` schema. Resolve unexpected states on a backup clone.

### Integration changes

| Consumer | Required action |
| --- | --- |
| `ghost.api.otp.send_otp`, `ghost.api.otp.validate_otp`, authentication APIs | Paths remain unchanged; apply the authentication contract changes above |
| Old `ghost.ghost.doctype.otp.otp` Python imports, including `OTP`, `generate`, `verify` | Deprecated module alias retained; move to `ghost.ghost.doctype.ghost_otp.ghost_otp` and class `GhostOTP` |
| `frappe.get_doc("OTP", ...)`, queries, explicit DocType strings | Change to `Ghost OTP` |
| `/api/resource/OTP` | Change to `/api/resource/Ghost%20OTP`; existing permission checks still apply |
| SQL using `tabOTP` | Change to quoted `` `tabGhost OTP` ``; update query reports and scripts |
| Desk routes/bookmarks | Use the Ghost OTP route (`ghost-otp`) appropriate to the Frappe version |
| App-owned fixtures, Customizations exports, JS/Python/Server Scripts, query text | Review and update hard-coded names before deployment |

The Python alias is not a second DocType. **There is no transparent alias for old resource
URLs, raw SQL or arbitrary `frappe.get_doc("OTP", ...)` calls.** Guests still cannot read OTP
resources. Use the public delivery/authentication methods rather than exposing code records.

### Upgrade and rollback verification

1. Inventory integrations/customizations; update hard-coded references and pause traffic,
   workers and scheduled tasks using OTP during the maintenance window.
2. Back up database/files and pin the previous code revision; rehearse on a clone.
3. Run `bench --site <site> migrate` with the candidate; verify existing record counts/names,
   native references, customization values, OTP delivery/consumption and configured policies.
4. Run migration again to verify idempotence. Both v15/v16 CI jobs include a previous-public-
   code install with real legacy/customized fixtures; require green checks for this revision.
5. Roll back using the matching tested database/files/code backup. Native table rename is DDL;
   changing code alone cannot revert the schema. Never automatically rename another app's data.
6. Announce the new internal name, required consumer edits and other breaking contracts in
   the approved major release notes and Marketplace update description before distribution.

See [the compatibility report](COMPATIBILITY_REPORT.md) for current evidence and limits.

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
   explicitly set OTP/signup policy, restart web/workers through the normal deployment
   procedure, and revoke affected credentials as planned.
6. Verify real mailbox delivery, login, logout, refresh, CSRF and app-specific ownership
   in staging, then smoke-test the live cutover. Google needs actual provider credentials.
7. Publish a versioned changelog and migration notice before Marketplace distribution.
