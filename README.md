# Ghost

**Ghost** is a specialized app for managing Guest User identities, OTP-based authentication, and Ghost authentication flows in Frappe.

## Features

-   **OTP Management**: Generate, send (Email/SMS), and validate One-Time Passwords.
-   **Ghost Users**: Create temporary "Ghost" users for guest sessions without requiring full registration.
-   **Rate Limiting**: Built-in security to prevent OTP spamming.
-   **Auto-Cleanup**: Scheduled tasks to remove expired Ghost users and OTP logs.

## Installation

1.  Get the app:
    ```bash
    bench get-app ghost [URL]
    ```

2.  Install on your site:
    ```bash
    bench --site [site-name] install-app ghost
    ```

## Usage

### OTP Generation
Refer to the `OTP` DocType to configure settings.
API endpoints:
-   `/api/method/ghost.api.otp.send_otp`
-   `/api/method/ghost.api.otp.validate_otp`

### Ghost Users
API endpoints:
-   `/api/method/ghost.api.ghost.create_ghost_session`

## License

MIT
