# CoastYouth Retail Update Certificates — v0.64.1

Desktop update checks and installer downloads now use a bundled public certificate-authority list alongside the computer's existing trusted certificates. This addresses missing public issuer certificates that can prevent DESK from checking GitHub for updates even when the same page opens in Edge. Certificate, hostname and installer checksum verification remain enabled. Unknown, expired or wrong-site certificates still fail verification.

The startup update dialog gives readable guidance for certificate errors, has room for the message, and offers **Check again** and **Continue opening**. Retrying a failed check or download does not change connection settings or run an installer without the user's Update selection.

## Installation

- DESK **1.22.1**
- OFFICE **1.19.1**
- STORE OPS desktop **1.6.1**
- Server / Server Admin / Computer Setup **0.64.1**

If the old DESK updater shows a certificate error, download the new DESK installer in the browser. Finish or save work, exit DESK, and install over the existing DESK installation under the same Windows account. Do not uninstall it or remove its settings. This one-time manual installation replaces the updater that cannot download its own fix.

**Updating only the server does not apply this desktop fix.** Install the affected desktop application update on each computer that needs it. A server already running 0.64.0 remains compatible with these clients; updating it is optional for this specific DESK correction. The all-in-one installer is also available.

The GitHub update connection is separate from the saved Operations server address. PIN sign-in still requires secure HTTPS access from other computers; this update does not remove that protection. Keep the existing terminal registration and use the configured secure server address.

All 0.64.0 checkout features remain included. No database schema or operational-record changes are required. Existing sales, credit balances/history, timecards, reservations, reports, users, attachments, terminal registrations, server addresses and exit passcodes are preserved. Publishing does not install anything on the live server or clients.

## Verification

TLS tests cover an empty default trust store, bundled public roots, retained system roots, and rejection of untrusted, expired and wrong-host certificates. Update checks, verified downloads, consent, retry, failed downloads, and configuration preservation are checked. Native packaging checks load the included certificate bundle before opening each desktop app.

Release checks also cover populated **0.64.0 → 0.64.1** upgrades, verified backups, repeated startup, rollback, and installation/reinstallation while preserving operational records and desktop settings.
