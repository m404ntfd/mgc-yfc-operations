# CoastYouth Retail Server Connection — v0.67.0

DESK, OFFICE and STORE OPS now show a themed connection dialog with the three-rings logo and a bouncing seven-bar indicator while connecting to the Operations server. Administrators can manage the connection timeout in OFFICE, and each client keeps the latest setting for its next startup, including when the server is unavailable.

## Connection and recovery

- The dialog says **Connecting to Server** and uses the application's saved theme colors. Reduced-motion preferences are respected.
- The default timeout is **10 seconds**. If the connection fails or times out, the logo remains with **Can Not Connect to Operations Server** and **Retry Connection**, **Configure Server Connection**, and **Log Out** options.
- Retry checks server connectivity without replaying a login, sale or payment. Late responses from an earlier attempt cannot override the current connection state. Existing unsaved-work and DESK exit-passcode protections remain in place.

## Timeout setting in OFFICE

- Open **OFFICE → System → Computers & versions → Server connection**. Administrators can select a whole-number timeout from **1 to 120 seconds**.
- Each application saves the server's setting on the client after a successful login, checks for changes when it loads and reconnects, and retains its last confirmed value while offline.
- Client connection setup shows the current timeout. The shared setting is managed in OFFICE. Local preference files contain appearance and timeout settings, not passwords or business records.

## Installation and automatic updates

- Server / Server Admin / Computer Setup: **0.67.0**
- DESK: **1.25.0**
- OFFICE: **1.21.0**
- STORE OPS desktop: **1.7.0**

Update the existing Operations server first, then update the installed desktop applications. The all-in-one installer can update the selected applications over their existing installations; keep the current server address and terminal registration. Desktop updates are required for the new native startup dialogs. Server updates supply the web screens and shared timeout setting.

The release is offered through the existing automatic update checks and OFFICE update controls. Publishing does not force an immediate installation. Clients that cannot download updates can use the browser-downloaded installer; certificate and checksum verification remain enabled.

## Data preservation and validation

The timeout setting uses a new, additive configuration table. Existing sales, reports, timecards, open punches and breaks, reservations and attachments, credit accounts, users, terminal registrations and audit history are retained. No production data or credentials are included in the release. Clover card payments remain disabled.

Release checks cover a populated **0.66.0 → 0.67.0** upgrade, backup, repeated startup and code rollback; administrator permissions and stale edits; timeout synchronization and offline caching; delayed connection responses; theme contrast; browser recovery; and installed Windows application startup.
