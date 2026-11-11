# CoastYouth Retail startup and update fixes

Server / Server Admin / Computer Setup 0.56.0 · DESK 1.17.0 · OFFICE 1.14.0 · STORE OPS desktop 1.3.0

## Changes

- Installed DESK, OFFICE, STORE OPS and standalone Server Admin check for updates when they start. A newer version offers Update or Not now. Selecting Update downloads and verifies the installer, closes the starting application, installs into its existing folder and reopens it. Offline or failed checks allow the application to open. A failed previous installation is reported instead of immediately repeating it.
- The shared server checks after startup. Selecting Update retains administrator sign-in, staff notification/readiness, backup and coordinated restart protections. The server and STORE OPS web app use the existing managed update process.
- OFFICE maximizes after successful sign-in, including a restored session. Failed sign-in keeps the normal login window. Staff can restore or resize OFFICE afterward without routine refreshes maximizing it again.
- DESK's My work is finished — update button records readiness separately from the download and countdown. The banner explains what it is waiting for, keeps download errors visible and offers Retry update download. Staff can choose Keep working while waiting. A new interaction cancels their readiness. Existing checks continue to block installation with unfinished sales, forms, pending writes or a shared-server update in progress.
- Download retry rechecks the active request and installer checksum. New DESK clients retain the original warning deadline; older clients can retry by restarting their warning period. Installers are instructed not to close other running applications or restart Windows automatically.

## Manual installation

1. Create and verify a fresh backup on the existing server. Finish sales and save all forms, then close the desktop clients. Use Exit server to stop the server before running its manual installer.
2. Install Server 0.56.0 over the existing installation, keeping its current folder and data location. Reopen it and confirm existing records are present.
3. Install DESK 1.17.0, OFFICE 1.14.0 and STORE OPS 1.3.0 on computers that use those apps. Keep each client's existing server connection. Computer Setup includes all installers; select only the applications needed on that computer.

The stuck update button can be bypassed by using these manual installers after work is saved and applications are closed. Startup checks take effect after this version is installed. The server update is required for the new DESK banner; the desktop installers add native startup checks and OFFICE maximization. The Server installer also offers standalone Server Admin for computers that use it separately.

## Data preservation and verification

No database schema changes or catalog imports are included. The release does not reset timecards, open punches or breaks, reservations, attachments, sales, accounts, products, prices, taxes, users, settings or terminal registrations. Existing installation IDs and data/configuration locations are preserved. Publishing does not install updates or restart a live store.

Checks cover startup consent and cancellation, offline and failed downloads, safe helper handoff, retry timing, unfinished-work protection, native OFFICE sign-in/maximization and browser update controls. Release checks also exercise a populated 0.55.0 upgrade, backup, repeated startup and rollback, plus real installers and client self-updates with retained settings and data.
