# Changelog

## [2.0.0] - 2026-02-08

### Changed
- **BREAKING**: Switched authentication method to OAuth2.
- Ghost sessions now return OAuth bearer tokens instead of API keys.
- All endpoints updated to require `Authorization: Bearer <token>` header.

### Added
- New `refresh_bearer_token` endpoint for token renewal.
- Token rotation on refresh (old tokens revoked).
- Automatic token invalidation on ghost-to-real user conversion.
- OAuth Token Settings tab in Ghost Settings with configurable expiration.
    - Access token expiry: 3600s (1 hour) default.
    - Refresh token expiry: 30 days default.
