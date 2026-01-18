# Ghost 👻

**Ghost** is a specialized Frappe application for managing Guest User identities and One-Time Password (OTP) authentication. It allows you to create temporary "Ghost" users for guest sessions and verify user identity via Email/SMS OTPs without requiring full registration.

## Features

### 🔐 Authentication (OTP)
-   **Multi-Channel Support**: Send OTPs via Email or SMS.
-   **Secure Validation**: Time-based expiry, consumption tracking, and secure random code generation.
-   **Rate Limiting**: Built-in protection against brute-force and spam (configurable limits).

### 👤 Identity (Ghost Users)
-   **Guest Sessions**: Instantly create temporary users (`ghost_randomID@guest.local`) with limited permissions.
-   **Auto-Cleanup**: Scheduled daily tasks automatically delete expired Ghost users and old OTP logs to maintain database hygiene.
-   **API Access**: Generates API Keys/Secrets for Ghost users for immediate client-side use.

---

## Installation

1.  **Get the App**
    ```bash
    bench get-app ghost https://github.com/muneeb141/ghost
    ```

2.  **Install on Site**
    ```bash
    bench --site [your-site] install-app ghost
    ```

---

## Configuration

### Ghost Settings
Search for **Ghost Settings** in the desk. All configurations are now consolidated here under two tabs: **Ghost Identity** and **OTP Configuration**.

-   **Enable Ghost Feature**: Master switch.
-   **Enable Auto Cleanup**: Turn on daily deletion of old users.
-   **Expiration Days**: How many days a Ghost user remains valid (Default: 30).
-   **Verify OTP on Conversion**: If enabled, users must provide a valid OTP code when converting to a real user.

#### OTP Configuration (Tab)
-   **Delivery Method**: Email, SMS, or Both.
-   **OTP Length**: Default 6 digits.
-   **Expiry Time**: Validity duration in minutes.
-   **Max Attempts**: Max OTPs a user can request per hour.

---

## API Reference

### 1. Send OTP
**Endpoint**: `/api/method/ghost.api.otp.send_otp`
**Method**: `POST`

```bash
curl -X POST https://your-site.com/api/method/ghost.api.otp.send_otp \
    -H "Content-Type: application/json" \
    -d '{"email": "user@example.com", "purpose": "Login"}' 
    # Purpose can be: "sign_up", "reset_password", "Login", "Conversion"
```

### 2. Validate OTP
**Endpoint**: `/api/method/ghost.api.otp.validate_otp`
**Method**: `POST`

```bash
curl -X POST https://your-site.com/api/method/ghost.api.otp.validate_otp \
    -H "Content-Type: application/json" \
    -d '{"email": "user@example.com", "otp_code": "123456", "purpose": "Login"}'
```

### 3. Create Ghost Session
**Endpoint**: `/api/method/ghost.api.ghost.create_ghost_session`
**Method**: `POST`
**Access**: Public (Allow Guest)

```bash
curl -X POST https://your-site.com/api/method/ghost.api.ghost.create_ghost_session
```

**Response**:
```json
{
    "user": "ghost_8f2a1c@guest.local",
    "api_key": "1234567890abcdef",
    "api_secret": "abcdef1234567890"
}
```
### 4. Convert to Real User
**Endpoint**: `/api/method/ghost.api.ghost.convert_to_real_user`
**Method**: `POST`
**Access**: System/Admin (or Privileged Context)

**Behavior**:
- If `real_email` exists: **Merges** the Ghost User's data (docs/logs) into the existing Real User.
- If `real_email` new: **Renames** the Ghost User to the Real User.

**Strict Mode**:
If "Verify OTP on Conversion" is enabled in settings, you **must** provide `otp_code`.

```bash
curl -X POST https://your-site.com/api/method/ghost.api.ghost.convert_to_real_user \
    -H "Content-Type: application/json" \
    -d '{
        "ghost_email": "ghost_xxx@guest.local", 
        "real_email": "real@example.com", 
        "first_name": "John",
        "otp_code": "123456" 
    }'
```
### 5. Centralized Login (Unified)
**Endpoint**: `/api/method/ghost.api.auth.login`
**Method**: `POST`
**Access**: Public

This is the primary endpoint for all client apps (Web, Mobile). It handles:
1.  **Direct Login**: Logs in guest with OTP.
2.  **Direct Signup**: Creates new user (with `Default User Role`) if missing.
3.  **Ghost Conversion**: Converts Ghost session to Real User (merging data).
4.  **Token Generation**: Returns OAuth Access Token (if `Client ID` is configured).

```bash
curl -X POST https://your-site.com/api/method/ghost.api.auth.login \
    -H "Content-Type: application/json" \
    -H "Authorization: token <ghost_api_key>:<ghost_api_secret>" \
    -d '{
        "email": "user@example.com", 
        "otp": "123456",
        "first_name": "New User"
    }'
```

**Response**:
```json
{
    "status": "success",
    "message": "Logged In",
    "user": "user@example.com",
    "access_token": "oauth_token_string", 
    "refresh_token": "refresh_token_string"
}
```

## License

MIT
