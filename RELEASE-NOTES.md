# CoastYouth Retail Computer Setup — v0.63.0

Computer Setup now verifies the Operations server connection and asks an administrator to register the computer in OFFICE after an interactive installation. It displays the current Windows computer name and keeps renaming optional. Registration runs whether the name changes or stays the same.

- Setup checks the administrator account and server compatibility before saving a connection. An unreachable server can be corrected and retried.
- The network adapter actually used to reach the server supplies its MAC address. A persistent Windows computer identity also keeps the same registration when the PC name, IP address or adapter changes.
- A matching MAC address with a different computer identity requires administrator confirmation before reusing the original registration. Ambiguous matches stop for review.
- Reinstalling reuses existing computer and checkout records. A unique previous application identity can be recovered when local settings are absent. Existing local identities are retained.
- Existing checkout store assignments and historical records stay in place. New checkouts can select a store or an available terminal. Removed checkouts require explicit confirmation to register again.
- Interrupted registration and local connection saves can be retried without creating another registration. DESK exit protection and other saved settings are retained.
- OFFICE shows the last reported server-connection adapter and MAC address. DESK, OFFICE and STORE OPS report this information when connected.
- Silent application updates retain their saved connections without interrupting staff with an installer sign-in.

## Installation

Versions: Server / Computer Setup **0.63.0**, DESK **1.22.0**, OFFICE **1.19.0**, STORE OPS desktop **1.6.0**.

Verify a current server backup and let staff finish or save their work. **Update the shared Operations server first**, then use Computer Setup on the other computers. The new registration step requires the updated server. For a brand-new server, start it and create its administrator account before completing registration.

Install over the existing applications and retain all data folders. This release adds registration bookkeeping tables; it does not reset or replace sales, timecards, reservations, reports, users, store settings or attachments. Publishing does not itself install or restart the live server; its configured update policy remains in effect.

## Verification

Checks cover administrator access, connection failures, repeated installs, PC and adapter changes, confirmed and ambiguous MAC matches, original checkout identity and store assignment, retry after a lost response or failed local save, and native wizard startup.

The populated **0.62.1 → 0.63.0** upgrade check verifies backups, repeated startup and rollback while retaining original rows, historical and open timecards and breaks, sales, accounts, reservations and attachments. Windows installer checks verify installation and reinstallation without replacing server data or saved client settings.
