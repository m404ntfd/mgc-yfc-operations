# CoastYouth Retail STORE OPS Photo Fix — v0.59.2

Request and appointment photos now open inside STORE OPS using the current sign-in. Previously, the View photo link opened the default browser, which could display “Please sign in again” because the desktop app and browser have separate sessions.

## Fixes

- View photo opens an in-app preview from pending requests, scheduled appointments, and the request editor, on desktop and mobile.
- Closing a photo returns to the same screen and preserves unfinished request edits.
- Photo access still requires sign-in and the existing permissions. No public attachment links or shared credentials are introduced.
- This release includes all previously published checkout, keyboard PIN, Credit/ Advances menu, training, printer, customer-display and update-policy changes.

## Installation and data preservation

Versions: Server / Computer Setup **0.59.2**, DESK **1.19.2**, OFFICE **1.16.2**, STORE OPS desktop **1.5.2**.

Verify a current server backup and update the shared server first. The server supplies the corrected STORE OPS screens to both the web app and desktop app. Reopen STORE OPS after the server update. Individual desktop installers and the combined Computer Setup installer are also provided.

Install over the existing applications and retain their data folders. This fix does not change the database schema or operational records. Existing timecards, punches, breaks, reservations, sales, photos, users, settings and terminal registrations are preserved. Publishing the release does not itself install or restart the live server; the configured server update schedule remains in effect.

## Verification

Checks cover the real Windows STORE OPS WebView2 window, desktop and mobile photo previews, multiple attachments, unauthorized access, missing-photo recovery, and preservation of unsaved request edits. Test appointment records and photo bytes remain identical after viewing.

Publication requires the application suites, Windows installer builds, fresh and repeat installations, and a populated **0.59.1** upgrade with backup and rollback verification. Tests use isolated synthetic records and destinations, never the live store database.
