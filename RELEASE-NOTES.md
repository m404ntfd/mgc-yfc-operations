# CoastYouth Retail DESK Touch Fixes — v0.59.1

This release fixes the clipped Credit/ Advances menu and keyboard PIN entry at startup. It includes all previously released training, checkout, printer, customer-display and update-policy changes.

## Fixes

- Store credit and Cash Advance open above the register's scrollable button column, with both buttons fully visible and clickable. The menu stays within the screen when resized and closes when tapping elsewhere, selecting an action, or pressing Escape.
- The PIN field receives focus immediately when sign-in appears, again when the desktop page is ready, and when returning to the sign-in page. Physical number keys and Enter work without first touching the text box, including after a failed PIN or switching from the touchscreen keypad.
- Native keyboard focus is restored only for the foreground DESK sign-in screen. Password fields, open dialogs, and other applications retain their focus.

## Installation and data preservation

Versions: Server / Computer Setup **0.59.1**, DESK **1.19.1**, OFFICE **1.16.1**, STORE OPS desktop **1.5.1**.

Verify a current server backup, update the shared server first, then update DESK and the other installed desktop applications. The server supplies the updated screens; DESK also needs its launcher update for the native keyboard-focus fix. Install over the existing applications and retain their data folders.

No database schema or operational-record changes are required for these fixes. Existing installation IDs, server connections, terminal registration, timecards, punches, breaks, reservations, sales, attachments, users and settings remain in place. Publication does not install or restart the live server.

## Verification

Checks cover keyboard-only PIN sign-in, failed-login recovery, password and dialog focus, mixed touch/keyboard entry, both green menu actions, and full menu hit targets at 1920×1080, 1366×768 and 1024×768 in Classic Gray, dark and glass themes. Native WebView2 startup, touchscreen checkout, store credit and cash advances are also checked.

Publication is gated on the full application suites, Windows installer builds, fresh and repeat installations, and a populated 0.59.0 upgrade with backup and rollback verification. All test records and destinations are isolated from the live store.
