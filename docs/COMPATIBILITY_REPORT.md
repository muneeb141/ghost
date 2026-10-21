# Ghost compatibility report

Date: 2026-10-21. Current integration branch: `develop`, based on the verified rename candidate
`ffba630` (`fix/ghost-otp-rename`, including `fix/auth-boundaries`).
Comparison: public `main` at `672dfec9346dfd935c87fdc6ded554014a36d7f4`.

## Develop standards and release follow-up

The first develop matrix passed v16 and quality but exposed a v15 joined-query ORDER BY
ambiguity in cleanup. The query now explicitly orders by the User creation column; require
the corrected matrix before promotion. The failed run is not counted as compatibility success.

The follow-up uses native filtered database updates/EmailTemplate methods, typed public APIs,
portal-only public signup roles and bounded native anonymous cleanup. It adds 14 database
regressions and repairs packaging/site-specific helper issues. See
[the source review and release gates](MARKETPLACE_REVIEW.md) and
[the contributor branch policy](../CONTRIBUTING.md).

| Local follow-up check | Result | Evidence |
| --- | --- | --- |
| Complete Ghost suite | 149 passed: 107 integration + 42 isolated | `/tmp/ghost-marketplace-full-tests.log` |
| HTTP login and owned conversion | Passed: HttpOnly session, follow-up, no default bearer credentials, replay denial | `/tmp/ghost-marketplace-http.log` |
| Migration and Ghost build | Passed | `/tmp/ghost-marketplace-migrate.log`, `/tmp/ghost-marketplace-build.log` |
| Isolated wheel and legacy setup shim | Passed; canonical schema/patch/license packaged and correct version reported | `/tmp/ghost-marketplace-build-wheel.log`, wheel metadata inspection |
| Frappe/Press scan | No blocking findings or scanner errors; advisory privilege/Guest warnings remain reviewed | `/tmp/ghost-marketplace-final.json`; suppression-disabled report also retained |
| Existing repository hooks | Passed; rerun with the final staged files before commit | `/tmp/ghost-marketplace-precommit.log` |
| Reviewed runtime `67e44a8`: v15/v16 fresh install and public upgrade | Passed: 149 tests on each of four sites, migration twice and native HTTP smoke | [Compatibility run](https://github.com/muneeb141/ghost/actions/runs/39577384176) |
| Reviewed runtime `67e44a8`: Frappe quality | Passed: all hooks, preflight, wheel/shim, 82 rules over 72 files; 19 warnings, no scanner errors or blocking findings | [Quality run](https://github.com/muneeb141/ghost/actions/runs/39577383969) |
| Ecom consumer regression follow-up | Earlier full run passed 14 cases but the new conversion case exposed provider-pin drift and an implicit-role guard error; after the external consumer fixes, its targeted new/existing-shopper conversion case passed | `/tmp/ghost-marketplace-ecom-conversion.log`; full consumer acceptance remains separately tracked |

The complete suite includes owned device A/B conversion to one verified account while an
unverified third session remains untouched; fixed test OTP acceptance only in automated tests;
HTML templates; Desk-role signup denial; native cleanup with staff/link protection and a real
session/savepoint rollback regression. Translation-only message fixes followed the local suite;
Both corrected CI jobs re-executed the complete suite successfully. A subsequent documentation-only
commit retains that runtime evidence; require green current-head checks before merging. Live provider/browser acceptance,
consumer restore/timing, release version/notices and hosted Marketplace approval remain open.
No zero-defect or complete security-audit guarantee is made.

## Decision

**This is a breaking authentication repair candidate, not a drop-in update to public 1.0.0.**
The current-site and CI results below verify the tested v15/v16 installations and upgrades.
They do not certify Marketplace distribution, external provider delivery or every consumer
application. Require the remaining deployment gates before release.
The new policy switches must be deliberately configured during an existing-site cutover.

The internal DocType is now `Ghost OTP`, table `tabGhost OTP`. A guarded pre-model-sync
patch migrates the old schema. Public OTP API paths and a deprecated Python import alias
remain; raw DocType/REST/SQL consumers require changes. See the [migration guide](API_MIGRATION.md).

## Rename candidate verification

The results in the historical evidence table below belong to the preceding authentication
candidate. They do not automatically certify this rename. The rename adds ten isolated guard/
import tests and a persisted fixture across two actual migrations, covering active OTP
consumption/replay denial, exact row values/counts, naming-series state, Custom Fields,
Property Setters, native Link/Dynamic Link values, file/share/comment/version references.
| Rename candidate check | Result | Evidence |
| --- | --- | --- |
| Real existing-site native rename and repeat migration | Passed; exact OTP row values/counts and series retained; custom fields, Property Setter and native references retained; active code accepted once | `scripts/smoke_otp_rename.py`, `/tmp/ghost-otp-rename-repeat.log` |
| Full local Ghost suite | 135 passed: 93 integration + 42 isolated | `/tmp/ghost-otp-rename-tests.log` |
| Ecom shopping regression after rename | 14 passed | `/tmp/ghost-otp-rename-ecom.log` |
| Native HTTP login and conversion | Passed; HttpOnly cookie, authenticated follow-up, no default bearer pair, replay denial | `scripts/smoke_email_otp.py` |
| Ghost build | Passed | `/tmp/ghost-otp-rename-build.log` |
| Installed v15 source isolated tests | 42 passed; does not modify its site/database | v15 command below, adding `ghost.tests.test_otp_rename` |
| Ruff and every configured pre-commit hook | Passed, including new files | Repository hooks, Ruff 0.8.1 |
| v15/v16 fresh install and previous-public-code upgrade | Required for this revision; inspect the current branch run for results | [Rename branch checks](https://github.com/muneeb141/ghost/actions?query=branch%3Afix%2Fghost-otp-rename) |

The initial local rehearsal caught a patch-registry path error and the public Frappe
wrapper's narrower rename signature before schema mutation. They were corrected to use
the registered patch module and native `frappe.model.rename_doc.rename_doc`; the successful
migration and repeated run then passed the persisted-data assertions. No framework source
was edited. The local fixture records/metadata were removed after verification.

A database/files backup was created before the local rehearsal on `ecom.localhost`:
`sites/ecom.localhost/private/backups/20261021_023057-ecom_localhost-*`. These are private
local artifacts and are not committed. A backup was created; full restore rehearsal remains
a consumer deployment gate.

## Environment

- Authorized disposable current site: `ecom.localhost` in the Ecom Bench.
- Frappe 16.51.1, ERPNext 16.50.0, Python 3.14.7, Node 24.21.0, MariaDB 10.11.14.
- Additional isolated checks use installed Frappe 15.121.1 source; its site/database were
  not changed. This is not a full v15 database run or a Python 3.12 runtime result.
- Ghost is tested as a general authentication app. Its fixtures do not require ERPNext.
  The current local site has ERPNext; both CI jobs verified Frappe-only installations.
- No local DB-admin access was available. The user selected the existing site for local
  tests. Separate clean-install and previous-release upgrade databases ran successfully in CI.
- CI observed Frappe 15.123.1 on Python 3.12 and Frappe 16.52.0 on Python 3.14.
  These are specific tested releases; the matrix follows their version branches.

## Historical authentication evidence (before the rename)

| Check | Result | Evidence |
| --- | --- | --- |
| Current-site migration | Passed | `/tmp/ghost-compat-migrate.log` |
| Complete Ghost suite on v16 | 125 passed: 93 integration + 32 isolated | `/tmp/ghost-compat-full-suite.log` |
| Legacy upgrade assertions | Included in the 93: eight-character identity/native User Link preservation, existing OTP retention/idempotence, security-setting migration, mixed-case configured domains | `ghost.tests.test_upgrade_compatibility` |
| Native HTTP login | Passed: direct login, HttpOnly sid, authenticated follow-up, no default bearer pair, cross-browser replay denial, owned Ghost conversion to verified cookie session | `/tmp/ghost-compat-http.log`, `scripts/smoke_email_otp.py` |
| Installed Frappe v15 isolated tests | 32 passed, real v15 source | Command below |
| Ecom shopping regression | 14 passed | `/tmp/ghost-compat-ecom.log` |
| Ghost asset build | Passed | `/tmp/ghost-compat-build.log` |
| Client examples | 13 Bruno endpoint paths/payload signatures resolve to whitelisted methods; two embedded demo scripts parse with Node. This is not Bruno CLI execution or browser interaction | One-off source-contract validation |
| Ruff | Full Python lint and formatting passed | Ruff 0.8.1, repository configuration |
| Existing pre-commit hooks | Passed: every configured hook | All tracked and new files included |
| Frappe 15.123.1 clean install and public-commit upgrade | Passed: 124 tests on each site, native HTTP smoke, legacy-data assertions and build | [v15 CI job](https://github.com/muneeb141/ghost/actions/runs/39490159009/job/118860885425) |
| Frappe 16.52.0 clean install and public-commit upgrade | Passed: 92 integration + 32 isolated tests on each site, native HTTP smoke, legacy-data assertions and build | [v16 CI job](https://github.com/muneeb141/ghost/actions/runs/39490159009/job/118860885009) |

Local logs are evidence paths, not committed artifacts; CI uploads its test/build logs
for reviewer access. The complete v15/v16 matrix evidence comes from the linked CI jobs,
separately from the local logs. Those jobs tested runtime commit `b286b9d`; the additional
mixed-case-domain regression was added afterwards. The final candidate runs the same matrix
with 125 tests per site; check the [current branch checks](https://github.com/muneeb141/ghost/actions?query=branch%3Afix%2Fauth-boundaries)
before merging. The linked historical jobs remain pinned evidence for the preceding 124-test revision.

## Regressions actually exposed and repaired

1. Ghost conversion through `auth.login` created an unused bearer credential for cookie
   login, and two active pairs for an explicit headless client. The real database tests
   failed on token counts before the fix. Conversion now leaves issuance to the caller
   so cookie login creates zero active pairs and explicit token login creates one.
2. A `Both` delivery challenge could contain a victim email and another person's phone;
   verification of the email alone accepted the shared code. A real persisted-row test
   demonstrated it. Generation and verification now require exactly one recipient;
   existing mixed-recipient records are rejected. `Both` chooses the requested channel.
3. Magic-link mail ignored the selected Ghost Email Account and required a site-default
   sender. The loopback SMTP test exposed it. Ghost now passes the selected sender to
   native `frappe.sendmail`, with native default fallback when none is configured.
4. Old fixtures assumed caller-named accounts, optional verification, fingerprint login
   and unconfigured OAuth clients. They now exercise the actual verified contracts with
   scoped records and unique fictitious recipient/domain names.
5. Patching a dynamic `frappe.local` attribute with `create=True` removed the framework's
   original flags during teardown on v16. All assertions passed but Bench exited with an
   error. The isolated-test helper explicitly restores prior context attributes; the full
   runner now exits successfully. No framework source was patched.
6. Legacy direct-login and Google Bruno requests used the wrong OTP purpose or a missing
   endpoint. Their payloads, environment handling and negative bypass example are updated.
   The playground requests a real code or consumes the emailed link from its original
   authenticated tab; it no longer offers a developer verification bypass.
7. Scheduled task helpers committed inside their caller's transaction. They now leave
   commit ownership to Frappe's request/job wrapper, making rollback-owned tests possible.
   This does not claim that the unchanged bulk cleanup handles every consumer app's data.

8. An existing site's mixed-case Ghost domain could fail the new anonymous ownership check
   because Frappe normalizes User emails to lowercase. A real existing-identity test failed
   with PermissionError before the fix. Anonymous creation and ownership matching now
   normalize the configured domain to lowercase and resolve the older mixed-case source payload
   to its canonical native User name; the exact owner, role and account checks remain.

## CI failures resolved before passing

The first attempt stopped before tests because Bench requires the `redis-server` binary
when rendering configuration, even when Redis runs in service containers. The runner now
installs it. The next attempt reached tests and exposed the skipped native Frappe asset
build: real email rendering requires `email.bundle.css` and the asset manifest. CI now
builds Frappe assets first. SMTP fixtures also accommodate v15 immediate and v16 deferred
queue timing while still asserting one actual wire message and successful use of its code.
The hook exclusion pattern was corrected so `.github` YAML is validated as well.
Neither failed attempt is represented as compatibility success; the linked corrected run
completed both matrix jobs successfully.

## What the tests exercise

- Real native User, OAuth Client/Bearer Token, OTP, Ghost Lead, conversion-log and
  magic-link records; role retention and new-account native rename/reference behavior.
- Source ownership, recipient/purpose binding, expired codes, replay rejection, disabled
  and built-in accounts, signup/staff policy, public response allowlists and Guest permissions.
- A failed conversion followed by rollback, and Redis guessing limits that survive a
  database rollback.
- Two independent DB connections racing to consume one OTP or rotate one refresh token;
  exactly one succeeds. These tests commit only their explicit fixtures and remove them.
- Local TCP SMTP reception using a real native Email Account, template and Email Queue;
  the code/link extracted from actual MIME messages is then consumed in authentication.
- Real loopback HTTP webhook delivery and HMAC over the exact received bytes.

Mock boundaries are explicit: isolated unit tests mock persistence; Google tests mock the
external provider response; transport tests use local servers, not an external mailbox.
SMTP tests suppress native queue commits only, keeping their real SQL/transport fixtures
rollback-owned. Native WSGI HTTP smoke tests use Werkzeug's cookie jar and temporary
committed fixtures with cleanup. They are not an automated multi-browser UI certification.

## Commands

From the Bench root, on the authorized disposable site:

```bash
bench --site ecom.localhost migrate
bench --site ecom.localhost run-tests --app ghost
bench --site ecom.localhost run-tests --app ecom --module ecom.services.test_shopping_integration
env/bin/python apps/ghost/scripts/smoke_email_otp.py ecom.localhost
bench build --app ghost
```

From the Ghost Git root, the v15 isolated check:

```bash
env PYTHONPATH=/home/muneeb_mohd/frappe/ecom/apps/ghost:/home/muneeb_mohd/frappe/livo/apps/frappe \
  PYTHONDONTWRITEBYTECODE=1 /home/muneeb_mohd/frappe/livo/env/bin/python -B -c \
  'import unittest; unittest.main(module=None, argv=["unittest", "ghost.tests.test_auth_boundaries", "ghost.tests.test_user_details"])'
```

## Remaining merge/release gates

1. Keep both compatibility jobs required and green on the revision being merged. Both
   passed for the tested runtime. Their real upgrade fixture includes legacy settings,
   an eight-character identity, an active OTP and a linked lead. It verifies retention,
   legitimate single-recipient code usability, mandatory verification and native links.
2. Rehearse an actual consumer clone's cutover and restore, including custom fields,
   domain/role policy, app-owned cart/booking/customer links, token refresh and existing
   target account ownership. Native rename can scan more linked tables than the old
   shortcut; measure it on a representative installation before setting timeouts.
3. Verify actual configured mailbox/SMS delivery and Google credentials, and the consuming
   browser/app's cookie, CSRF and magic-link handoff. Local SMTP acceptance is not inbox
   delivery, and mocked Google verification is not a live provider login.
4. Announce the breaking contracts, explicit OTP/signup enablement and affected-credential
   revocation policy. Keep native password login available during a planned cutover.
5. Choose a major release version and publish release notes after these gates pass.
   The approved rename is included in this major-update candidate and must pass its own
   fresh-install, previous-public-code upgrade and repeat-migration checks before release.

No main merge, tag, Marketplace publication or production deployment is performed by
these checks. The feature branch can be reviewed before the release gates are satisfied.
