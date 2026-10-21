# Contributing and releases

## Branch workflow

Keep `main` as the repository default and stable distribution branch. `develop` is the
integration branch for the next release. It is not approved for production deployment.

1. Create `feat/<topic>` or `fix/<topic>` from current `develop`.
2. Open a focused PR against `develop`; include API/configuration changes, migration notes,
   failure/recovery behavior and real regression evidence. Never add secrets or site backups.
3. Require the Frappe v15/v16 compatibility jobs and Frappe quality job on the PR revision.
   Review security-sensitive ownership/permission changes even when automated checks pass.
4. Merge reviewed work into `develop`. Resolve conflicts before rerunning checks.
5. Freeze a candidate on `develop` or `release/<version>`; complete the
   [Marketplace release gates](docs/MARKETPLACE_REVIEW.md), including live provider and restore checks.
6. Open a release PR from the frozen candidate to `main`. The maintainer explicitly authorizes
   the manual merge, version/tag and publication. No workflow enables automatic merging,
   Marketplace publication or production deployment.
7. Bring any release fixes on main back to develop before starting subsequent feature work.

Suggested GitHub protections for both long-lived branches: PR-only changes, required CI,
resolved review discussions, no force pushes/deletions. These settings require a separate
repository-admin configuration; documentation/CI does not prove protection is enabled.
Keep the publication source pointed at the approved stable branch/revision.

## Local verification

Use an explicitly disposable site; never run committed fixtures on a customer site.

```bash
pre-commit run --all-files
python scripts/check_marketplace.py
bench --site <disposable-site> run-tests --app ghost
bench build --app ghost
```

Run Bench commands from the Bench root, and the preflight/lint commands from the Ghost root.
The standalone preflight uses Python 3.12+ and `semantic-version`; they are developer tooling,
not new Ghost runtime dependencies. CI installs them outside the application package.
The HTTP/upgrade fixture scripts have narrower documented site-name guards.

The quality workflow scans the whole tracked app with pinned Frappe and Frappe Cloud Press
rules. It uploads ordinary and suppression-disabled scan reports. Scanner errors and blocking
findings fail the gate; warnings remain visible for manual review. Suppressions must name a
specific rule and explain the trust boundary in the review document. Do not add blanket
file exclusions or suppress a real defect to obtain a green check.

For UI/provider behavior, record the actual browser, transport and provider boundary tested.
Loopback SMTP is not external inbox delivery. A mocked Google response is not a real Google
sign-in. Coverage percentages and green pipelines cannot guarantee zero production defects.
