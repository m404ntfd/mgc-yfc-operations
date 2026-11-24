# CoastYouth Retail Clover Setup — v0.66.0

Administrators can prepare a registered DESK computer for a Clover connection test while merchant authorization is pending. **Card payments remain disabled.** This release cannot charge, refund, or cancel a Clover payment and does not create Clover orders.

## Clover connection setup

- In **OFFICE → System → Payment devices → Clover connection setup**, select the registered terminal and save its Clover local IP address, serial number, and optional confirmed merchant ID.
- On that computer, open **DESK → MORE → Clover connection setup → Check connection · no charge**. REST Pay Display must be running on the Clover and both devices must be on the same local network. The check reports which computer performed it.
- A reachable device is clearly distinguished from an authorized device. Clover approval and a later merchant-authorization step are still required; this release provides setup and network testing only.
- Administrator permissions are checked on the server. Tests use short-lived, single-use approval tied to the current terminal, administrator session, and saved configuration. Certificates remain verified. No token, password, API key, or card-number entry is requested.
- Store transfers require the administrator to reconfirm Clover settings. Duplicate serial assignments and stale edits are rejected. Existing terminal registrations, receipt settings, taxes and transactions remain intact.

## Online donation request controls

This release also includes the previously prepared **Pause Online Requests** control in Dispatch's Pending Requests box. Authorized staff can pause requests across coastyfc.com, thriftmart.coastyfc.com and binopoly.coastyfc.com for **8, 12 or 24 hours**, see current status, or resume early. Requests remain active by default. Customers see a reopening notice when entering the item-donation flow. Existing requests and appointments are retained, staff can continue managing them, and monetary giving is unaffected.

## Installation and automatic updates

- Server / Server Admin / Computer Setup: **0.66.0**
- DESK: **1.24.0**
- OFFICE: **1.20.0** (unchanged launcher; server supplies the new setup screen)
- STORE OPS desktop: **1.6.1** (unchanged launcher; server supplies current screens)

Update the existing Operations server first. Then use the all-in-one installer on **pos1**, selecting **POS checkout**, to update DESK. Install over the existing versions; do not uninstall or remove application data. Keep the existing server address and terminal registration. The release is offered through the existing update checks and OFFICE update controls; publishing does not force an immediate installation.

Older clients that cannot download updates because of a certificate error can use the browser-downloaded installer. Certificate and checksum verification remain enabled.

## Data integrity and validation

Only additive Clover-configuration and online-request-settings tables are introduced. Existing sales, reports, timecards, open punches and breaks, reservations and attachments, store-credit records, users, and terminal history are preserved. No payment processing is enabled and no production data is included in release files.

Release checks cover a populated **0.65.0 → 0.66.0** upgrade, backup, repeated startup and code rollback; permission and configuration isolation; TLS and authorization restrictions; light/dark theme readability; preserved active carts; and actual installed Windows application startup. Automated Clover device responses use isolated fixtures. The real authorized connection on pos1 remains pending Clover approval and merchant authorization.
