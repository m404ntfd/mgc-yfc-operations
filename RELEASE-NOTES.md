# CoastYouth Retail remote connections and recovery

Server / Server Admin / Computer Setup 0.57.0 · DESK 1.18.0 · OFFICE 1.15.0 · STORE OPS desktop 1.4.0

## Remote connections

- Native connection checks, administrator approval requests, Server Admin requests and desktop update requests identify themselves as CoastYouth Retail. This resolves the Cloudflare rejection of the default Python client signature without weakening certificate verification or changing website security settings.
- DESK, OFFICE and STORE OPS verify the configured server before opening their work screen. When the server is unavailable, a connection screen offers Retry connection, Change server and Close. Staff can connect their VPN and retry without restarting the application.
- A changed address is saved only after a successful check. Failed, canceled, denied or abandoned checks retain the previous address and device identity. DESK retains its administrator exit-passcode requirement for changing an existing protected connection.
- Entering operations.coastyfc.com without a scheme uses HTTPS. Local server names/IP addresses remain supported. Connection checks do not follow redirects, send credentials or change server records.
- STORE OPS receives the same connection recovery options. Standalone Server Admin retains its existing editable address and Test connection controls.

## Connecting from another network

Install the desktop clients needed on that computer, then use https://operations.coastyfc.com as the server address. Use the base address only, without /office or /pos. Sign in using the existing server account and complete administrator terminal registration if this is a new computer.

Alternatively, connect the computer to the store VPN and use the server address accessible through that VPN. If the VPN is disconnected when the application opens, connect it and select Retry connection. Change server allows correction of an old IP address or switching to the public HTTPS address.

The existing store server must be running and reachable. These clients use its existing database; no second server or data copy is needed. Offline checkout is not provided. A connection interruption during existing work does not automatically reload or switch servers; existing unsaved-work and transaction-retry protections remain in place.

## Installation and data preservation

Create and verify a fresh backup before updating the server. Finish transactions and save forms; close desktop clients. Use Exit server before manually installing the server update. Install over existing folders and retain the existing data location and connection settings. Do not uninstall or reset data. Computer Setup lets you select the applications needed on each computer.

No database schema, operational records, account permissions or catalog imports are changed by this release. Timecards, open punches/breaks, reservations, attachments, sales, products, prices, taxes, customers, users, settings and terminal registrations remain in the shared server. Publishing does not install updates or restart the live server.

Release checks cover identified native requests, HTTPS verification, redirect refusal, VPN retry, verified address changes, canceled/denied/failed saves, initial setup, retained device settings, real desktop clients, populated 0.56.0 upgrade/backup/rollback, and Windows installers/self-updates. Read-only checks also verified the updated connection code against the public operations.coastyfc.com endpoint; no live records or credentials were used.
