# Device identity, test OTP and verified account convergence

Status: design clarification for the unreleased major-update candidate. Features explicitly
listed as future work are not implemented by this document.

## Device identity

An IP address identifies a network attachment, not an authenticated person. Public addresses
can be shared by Wi-Fi/cellular users, change on travel or VPN use, and be hidden by proxies.
A private/device interface address is not a global durable identity. A hardware/MAC address
is not a general-purpose identifier available to an ordinary website. Browser fingerprints
are observable characteristics; hashing them does not turn them into secret credentials.
Use IP/fingerprint signals only as optional, privacy-aware abuse/risk inputs, never to issue
credentials, recover an account or select a merge source. Ghost already uses an IP verification
limit; it does not use IP as login proof. Shared networks can affect that limit and need staging
validation behind the actual trusted reverse proxy.

Current Ghost anonymous creation issues a random server identity plus bearer credentials.
Current same-origin verified login creates a native Frappe HttpOnly session. A future optional
browser remember-device feature should use an expiring, random, revocable secret protected by
Secure/HttpOnly/SameSite cookies, token rotation and CSRF controls. Clearing it requires fresh
verification. Never recreate it from a fingerprint. Device-bound key proofs can be evaluated
later; passkeys can also be synced, so a passkey is not necessarily tied to one physical device.

## Fixed OTP for tests

The fixed-code sandbox remains available when the framework is executing automated tests
(`frappe.flags.in_test`). It deliberately substitutes proof for test setup and does not model
production recipient binding, expiry or single-use behavior. Production tests must exercise
real generated, persisted challenges in addition to these sandbox tests.

Previously a public/staging deployment could enable a predictable code and accept it for
an arbitrary supplied recipient. Knowing that code could satisfy the OTP step, subject to the
other flow prerequisites. Source ownership alone did not prove the target email. This is a
code-path risk, not evidence of an actual compromise. The candidate rejects fixed-code generation
and verification outside automated tests; ordinary migration disables a saved sandbox setting.
A browser/manual test should use generated codes delivered through a controlled test mailbox
or local SMTP sink with test-only accounts. Do not enable a universal code on a reachable site.

## Same email after verification

Supported: device A owns Ghost A, verifies alice@example.com and converts its own source.
Device B owns Ghost B, independently verifies that account and converts its own source into
the existing Alice account. There is still one target User; existing roles are preserved.
Ghost-owned OTP references are reassigned and anonymous bearer credentials revoked.
Public signup cannot assign a Desk-capable role, even when OTP login for existing staff is enabled.

Not supported: search every unverified captured lead for alice@example.com and claim all its
Ghost sessions after verifying Alice once. Someone else could have typed Alice's email into a
session containing their private data. Verification proves the destination; source credentials
or explicit source consent must also prove every source being moved.

New-account native User rename follows native User Link references. Conversion into an existing
User automatically reassigns only the documented Ghost-owned references, not arbitrary cart,
booking, patient or customer records. A consumer owns its migration policy, permissions,
idempotency and conflict handling. An app's raw Data/Text ownership fields are not native Links.
The old internal bulk-merge helpers are not a supported public verified-merge API.

## Proposed roadmap, in order

| Priority | Feature | Acceptance boundary |
| --- | --- | --- |
| Release | Staging provider/browser/restore evidence and Marketplace review | Close the documented release gates before publication |
| Next | Delivery diagnostics and OTP policy visibility | Administrator-only diagnostics; public responses reveal no account existence or secrets |
| Next | Session/device listing and selective revocation | Native sessions/OAuth records, ownership checks, no credential exposure |
| Next | Remember-device browser credentials | Random expiring secrets, revocation/rotation, CSRF, no fingerprint recovery |
| Later | Explicit cross-device linking/merge grants | Verify target and every source, short-lived single-use grant, consumer-controlled business-data move |
| Later | Passkeys/WebAuthn | Reuse native Frappe support where available; verify v15/v16 gaps before introducing another credential store |
| Later | Generic reusable portal login components | Branding/localisation/accessibility; no commerce-specific dependency |
| Later | Broader abuse controls and delivery recovery | Proxy-aware limits, enumeration resistance, burst/load tests and audited provider outcomes |

No future feature is activated by this branch-policy/documentation update.

Sources: [W3C fingerprinting guidance](https://www.w3.org/TR/fingerprinting-guidance/),
[MDN WebAuthn](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API).
