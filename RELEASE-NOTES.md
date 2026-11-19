# CoastYouth Retail Connection Recovery — v0.62.0

OFFICE and DESK now give staff a way to recover when a server cannot be reached or a computer needs registration. Users can correct the server address, retry the connection, and sign in with an administrator account to register the PC.

## Connection and registration

- The Windows startup connection screen offers Retry connection, Change server, and Register / configure PC.
- Server connection / register PC is also available before sign-in. Terminal setup and registration-error screens include Server address / reconnect.
- New addresses are verified before saving. Failed or canceled checks leave the previous connection in place. The app retains its computer identity, saved settings, and DESK exit protection.
- Changing the DESK server still requires its existing admin exit passcode. Registration requires an administrator account on the connected server; regular staff cannot register a computer.
- Unsaved work blocks connection changes. Passwords entered for administrator sign-in are sent through the existing sign-in process and are not stored in desktop connection settings.

## Re-registering a removed checkout

- An administrator can explicitly re-register the original terminal directly from its recovery screen.
- The original terminal identifier, store, layout, printing settings and historical records are retained. A duplicate terminal is not created.
- Re-registration is recorded in the audit log. Simply restarting or reconnecting a removed checkout does not reactivate it.
- Sales, receipts, reports, timecards, reservations, attachments, customers, users, products and other business data remain intact.

## Installation

Versions: Server / Computer Setup **0.62.0**, DESK **1.21.0**, OFFICE **1.18.0**. The compatible STORE OPS desktop **1.5.2** is included in Computer Setup.

Verify a current server backup and let staff finish/save their work. **Update the shared server first, then update OFFICE and DESK.** The new recovery screens and native connection controls require the matching server and desktop updates together. Install over the existing applications and keep their data folders and connection settings.

Publishing does not itself install or restart the live server; its configured update policy remains in effect. The operations web app remains available.

## Verification

Release checks cover administrator permissions, failed and canceled connections, saved-address preservation, exit-passcode protection, unsaved work, re-registration without duplicate terminals, retained sales/report totals, and existing registration workflows in all three desktop applications.

The populated **0.61.0 → 0.62.0** upgrade check verifies backup, repeated startup and rollback. It checks original records and identifiers, historical and open timecards/breaks, reservation attachments, registered computers, and retained terminal-removal history. Windows installer checks verify installation and reinstallation without changing existing data and settings files.
