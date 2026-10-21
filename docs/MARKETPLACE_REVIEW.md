# Marketplace code review and release readiness

Review date: 2026-10-21. Integration branch: `develop`. Public baseline: `672dfec`.
This is a source/test readiness report, not a Frappe Cloud approval or a penetration-test certificate.
The repository default remains `main`; the candidate has not been merged there or released.

## Actual Frappe Cloud checks inspected

The official app authoring guide requires passing CI and recommends the Frappe Semgrep rules.
The inspected Press auditor additionally checks metadata, dependency declarations, versioning,
code-quality hooks, compatibility with configured benches/sources, and security/correctness rules.
Some checks query the actual Frappe Cloud records; a local script cannot certify those.

Primary sources, inspected on the review date:

- [App authoring guidelines](https://docs.frappe.io/cloud/marketplace/app-authoring-guidelines)
- [Publishing requirements](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines)
- [Frappe Cloud Press auditor](https://github.com/frappe/press/tree/99347cbb73775997eac9b36d6f9a0d39295a3735/press/marketplace/doctype/marketplace_app_audit/checks)
- [Frappe Semgrep rules](https://github.com/frappe/semgrep-rules/tree/81a6e3d47a328249e8ddf04c586e493dd5553002)

The separate frappe/marketplace registry/Pilot publication workflow is not assumed to be the
Frappe Cloud dashboard submission process. No registry PR, dashboard release, tag or deployment
is created by these changes.

## Findings and fixes

| Finding | Action | Verification boundary |
| --- | --- | --- |
| Dynamic SQL for configured lead status and OTP reference reassignment | Use native `frappe.db.set_value` with filters and parameterized values | Real conversion/lead tests, role retention and native references |
| Direct template rendering | Use native EmailTemplate formatted subject/response methods | Real loopback transport plus new HTML-template regressions; templates remain administrator-controlled |
| Public signup could inherit a Desk role when staff OTP login was enabled | Reject Desk-capable roles for all new public accounts, independently of existing staff login policy | Direct signup and conversion reject before creating/renaming/revoking source credentials |
| Missing public input types | Annotate public API parameters | Native dispatch/HTTP tests and complete v15/v16 compatibility suite |
| Raw bulk User/child-table deletion | Use bounded native deletion with exact anonymous naming, Website User and role checks | Native tokens/children cleanup, staff/caller-named protection, retained native links, rollback |
| Linked expired anonymous records | Keep User and references; disable identity, revoke bearer credentials and clear sessions | Real linked Ghost Lead regression; arbitrary consumer Text/Data ownership is outside native Link discovery |
| Fixture permission assertion flagged by scanner | Assign/check the boolean result explicitly | Existing fresh/upgrade fixture assertions retained |
| Legacy root helper scripts targeted a hard-coded site/path | Disable those obsolete helpers with clear Desk/fixture instructions; preserve callable names for an explicit error | No connection or writes occur on import or invocation |
| Test scripts need committed state between CLI processes | Narrow documented commit annotations, with disposable-site and allow_tests guards | Two actual migration invocations and HTTP fixture cleanup |
| Native application hook dispatcher flagged as code execution | One rule-specific reviewed exception; handler comes from installed app hooks | Existing hook/webhook tests; no HTTP parameter supplies a dotted handler |

The legacy setuptools shim imported version from an empty subpackage; it now uses the canonical
`ghost.__version__`. Wheel and shim checks verify packaging. SPDX license metadata and public
project/support links are declared without adding Ghost runtime dependencies.

Cleanup selects at most 100 enabled candidates per run, respects a smaller configured batch and never
forces deletion through native links. Unlinked identities are deleted through Frappe; linked
ones are disabled and retained. No universal erasure/privacy-compliance guarantee is made.
Native deletion does more work than raw SQL; representative deployment timing remains required.
Cleanup runs only in a background/CLI context. Linked-user session clearing waits until commit
and rechecks disabled state, because native session deletion commits its own database work.
Disabled retained identities are not repeatedly selected ahead of other eligible users.

## Scanner results and exceptions

Initial combined scan: 75 findings, including blocking patterns. After the native API/type
fixes: no scanner errors or unsuppressed blocking findings; 19 remaining warnings (12 distinct source sites; overlapping rule sets repeat privilege warnings) concern the
intentional Guest authentication endpoints and `frappe.set_user` boundaries. The final CI
artifacts/counts are authoritative for the revision being reviewed.

Semgrep is pinned to 1.182.0. Both upstream rule repositories are pinned above so results are
repeatable. Review rule updates through a separate PR. The scan gate uses Press's blocking
metadata and Critical/Major severity mapping; it does not mistake process exit 0 for no findings.
All advisory findings are printed. A second report disables `nosemgrep` so reviewers can inspect
all annotated code, rather than losing that evidence behind a green gate.

Reviewed exceptions:

- `ghost/events.py`: `frappe-codeinjection-eval` for `frappe.call` of `ghost_conversion_hooks`
  installed through app hooks. These are trusted server extension points, never request input.
  Hook failures are logged; no credentials are included in the event payload. This remains a
  manual security-review surface, not an automatic promise that every installed hook is safe.
- `scripts/compatibility_site.py`, `scripts/smoke_email_otp.py`, `scripts/smoke_otp_rename.py`:
  `frappe-manual-commit` only at fixture stage boundaries/cleanup. They are unwhitelisted CLI
  tools, require explicit allow_tests and narrow disposable site names, and use fictitious data.
  Production services must not copy their commit or privilege patterns.
- Older annotations on constant parameterized SQL do not grant approval to new dynamic SQL.
  Do not add broad `.semgrepignore` exclusions or disable a rule to conceal a defect.

Privilege warnings in `ghost/api/ghost.py` cover the private conversion block: source ownership
and target proof are checked before escalation; the original actor is restored in `finally`.
Guest warnings cover intentionally public code delivery, verification, login, anonymous issuance
and refresh. Their ownership, proof, policy, origin and rate-limit behavior must remain reviewed.
Warnings in scripts cover their guarded setup/teardown only.

## Release evidence and outstanding gates

- Prior candidate `ffba630`: [green v15/v16 fresh-install and public-upgrade matrix](https://github.com/muneeb141/ghost/actions/runs/39498208057), 135 tests per site.
- This follow-up adds 14 real database regressions (seven identity/template cases, five
  cleanup/session safety cases and two public-role cases). Require the new quality job and both compatibility jobs on its final
  revision; prior green checks do not certify changed code.
- Local follow-up evidence is recorded after verification in COMPATIBILITY_REPORT.md.
- Native HTTP smoke and build must also pass after the runtime changes.

Before promoting the major release:

- [x] Reviewed runtime `67e44a8` passes Frappe quality and both v15/v16 fresh/upgrade jobs.
  [Compatibility](https://github.com/muneeb141/ghost/actions/runs/39577384176) /
  [Quality](https://github.com/muneeb141/ghost/actions/runs/39577383969). Require green checks again on the revision being merged.
- [ ] Review unsuppressed scanner evidence and source trust boundaries.
- [ ] Rehearse a representative consumer's upgrade, rollback restore and native rename/cleanup timing.
- [ ] Verify real mailbox delivery, configured SMS and Google sign-in for the features advertised.
- [ ] Verify the consuming browser's cookies/CSRF and magic-link handoff; loopback SMTP/mocked Google are not live acceptance.
- [ ] Review any affected legacy credentials and communicate reauthentication/revocation.
- [ ] Assign the approved major version, dated changelog and Marketplace migration notice.
- [ ] Confirm the actual Cloud listing's description, screenshots/logo, support/privacy URLs,
  category, source branch/revision and currently installed bench compatibility in the hosted audit.
- [ ] Configure required status checks/PR protection in GitHub; workflows alone are not branch protection.
- [ ] Maintainer explicitly authorizes the manual main merge, release/tag and publication.

The listing must describe tested capabilities without universal security, GDPR, performance or
zero-defect claims. A 200px+ logo, current screenshots, valid publisher contact and support/privacy
links need checking in the actual listing. The source includes a
[privacy/data-handling disclosure](PRIVACY.md); confirm the listing points to its approved public URL.

## Published listing review and prepared update

The public listing was inspected on 2026-10-21. It still contains old fingerprint/automatic-merge,
direct-SQL/performance and universal data-loss/privacy claims plus repeated description sections.
The privacy resource leads to the older general GitHub Pages documentation. A concrete
[replacement listing and update notice](MARKETPLACE_LISTING_DRAFT.md) is prepared for review;
it is not submitted. The existing 300px square icon meets the documented minimum dimensions.
Uploaded screenshots, source/release selection and hosted audit still require dashboard checks.
