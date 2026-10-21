# Ghost data handling

This disclosure describes the unreleased Ghost candidate's data handling. Each site operator
is responsible for their deployment's privacy notice, legal basis, retention and access controls.
It is not a universal compliance certification or a promise of complete automatic erasure.

Ghost runs inside the site's Frappe installation. Depending on enabled features it stores native
Users/roles and credentials, temporary OTP challenges, magic-link records, captured lead email,
conversion logs and configurable provider/delivery settings. Existing databases may also contain
legacy fingerprint records; this candidate does not use fingerprints to authenticate accounts.
Verification rate limits use site-scoped Redis keys derived from the recipient/purpose and request
IP, with short expiry. Hashing these keys does not make the overall service anonymous.

Email/SMS delivery sends recipient and message data through the operator's configured provider.
Google conversion verifies a supplied identity token with Google. Optional webhooks send conversion
identity/event data to the operator's configured endpoint; credential values are excluded from
the webhook payload. Ghost does not activate an external analytics service by default.

Authentication records and backups require restricted administrator/database access. OTP values
are stored in restricted challenge records for their lifecycle; this candidate does not claim
that all credential/challenge material is hashed at rest or automatically removed on expiry.
Expiry prevents authentication with an expired code and is separate from deletion of its record.
Never expose OTP resource data to a frontend, publish credentials or include them in support logs.

Configured jobs expire OTPs, prune old conversion logs and clean up expired anonymous identities.
Cleanup preserves native linked records and disables linked expired identities instead of forcing
deletion. It cannot infer every consuming app's Data/Text ownership, historical exports or backups.
The site operator must review business records, legacy fingerprints, tokens, challenge records,
Email Queue, server logs and backups when implementing access, retention or erasure requests.

The app maintainer does not receive site records merely because Ghost is installed. If requesting
support, redact personal data and secrets. Report ordinary bugs through
[GitHub Issues](https://github.com/muneeb141/ghost/issues). Do not publish vulnerabilities, codes,
tokens, site backups or private account details in a public issue; arrange private security contact
with the maintainer before sharing sensitive reproduction details.
