# Ghost API - Bruno Test Collection

This directory contains a [Bruno](https://www.usebruno.com/) API test collection for the Ghost app.

## About Ghost

Ghost provides anonymous user identity management with OAuth2 bearer token authentication for Frappe applications. It allows users to browse as "ghost" users and later convert to authenticated users.

## Prerequisites

1. **Install Ghost App**
   ```bash
   bench get-app https://github.com/yourusername/ghost
   bench --site your-site install-app ghost
   ```

2. **Configure Ghost Settings**
   - Go to: Setup > Ghost Settings
   - Enable Ghost Feature
   - Create an OAuth Client (Setup > Integrations > OAuth Client)
   - Set the Client ID in Ghost Settings

3. **Install Bruno** 
   - Download from: https://www.usebruno.com/
   - Or via CLI: `npm install -g @usebruno/cli`

## Setup

### 1. Update Base URL

Open each `.bru` file and update the `baseUrl` variable to match your site:

```javascript
vars:pre-request {
  baseUrl: http://your-site.localhost:8000
}
```

Or set it globally in Bruno's environment variables.

### 2. Update Test Data

For conversion tests, update the email and personal data in:
- `Convert (Secure).bru`
- `Send OTP (Conversion).bru`

Replace `user@example.com` with your actual email to receive OTP codes.

## Test Flow

### Basic Flow (Recommended Order)

1. **Create Ghost Session** 
   - Creates anonymous ghost user
   - Returns OAuth bearer tokens
   - Stores `access_token`, `refresh_token`, `ghost_email` in variables

2. **Refresh Token** (Optional)
   - Tests token refresh flow
   - Returns new access_token and refresh_token

3. **Send OTP (Conversion)**
   - Sends OTP to real user's email for verification
   - Replace email with your test email

4. **Convert (Secure)**  
   - Converts ghost user to real user
   - Requires valid OTP code from step 3
   - Returns new tokens for authenticated user

### Variables Auto-Set by Tests

The tests automatically set and use these variables:

| Variable | Set By | Used By |
|----------|--------|---------|
| `ghost_email` | Create Ghost Session | Convert (Secure) |
| `access_token` | Create Ghost Session, Refresh Token | Convert (Secure), Refresh Token |
| `refresh_token` | Create Ghost Session | Refresh Token |
| `real_email` | Convert (Secure) | Future requests |

## API Endpoints

### 1. Create Ghost Session

**Endpoint:** `POST /api/method/ghost.api.ghost.create_ghost_session`

**Authentication:** None (guest allowed)

**Response:**
```json
{
  "message": {
    "user": "ghost_abc123@guest.local",
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

### 2. Refresh Token

**Endpoint:** `POST /api/method/ghost.api.auth.refresh_bearer_token`

**Body:**
```json
{
  "refresh_token": "your_refresh_token"
}
```

**Response:**
```json
{
  "message": {
    "status": "success",
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

### 3. Send OTP

**Endpoint:** `POST /api/method/ghost.api.otp.send_otp`

**Body:**
```json
{
  "email": "user@example.com",
  "purpose": "Conversion"
}
```

### 4. Convert Ghost User

**Endpoint:** `POST /api/method/ghost.api.ghost.convert_to_real_user`

**Authentication:** Bearer token required

**Headers:**
```
Authorization: Bearer <access_token>
```

**Body:**
```json
{
  "ghost_email": "ghost_abc123@guest.local",
  "real_email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "otp_code": "123456"
}
```

## Authentication

All authenticated requests use OAuth2 Bearer tokens:

```
Authorization: Bearer <access_token>
```

**Never use API keys** - Ghost uses industry-standard OAuth2 bearer tokens.

## Token Lifecycle

- **Access Token**: Valid for 1 hour (configurable in Ghost Settings)
- **Refresh Token**: Valid for 30 days (configurable)
- **Token Rotation**: Refresh endpoint returns new tokens and revokes old ones

## Troubleshooting

### "OAuth Client ID is required"

- Ensure Ghost Feature is enabled in Ghost Settings
- Create an OAuth Client in Frappe
- Set the Client ID in Ghost Settings

### "Invalid or expired refresh token"

- Tokens expire after configured time
- Create a new ghost session to get fresh tokens

### "OTP Code is required for conversion"

- Enable "Verify OTP on Conversion" in Ghost Settings
- Send OTP via "Send OTP (Conversion)" request first
- Check your email for the OTP code

### Variables not updating

- Ensure Bruno's scripts are enabled
- Check the post-response scripts in each request
- Verify response status is 200

## Contributing

When contributing tests:
1. Use placeholder data (no real emails/names)
2. Use `http://localhost:8000` as baseUrl
3. Document new endpoints in this README
4. Keep tests in logical order

## License

MIT License - Same as Ghost app

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/ghost/issues
- Documentation: See main Ghost README

---

**Tip:** Run tests in sequence for the first time to understand the full authentication flow!
